# -*- coding: utf-8 -*-
import sys, pygame
from pygame.locals import *
import time
import os
import logging
import datetime
from math import ceil, floor
from datetime import timedelta
from signal import alarm, signal, SIGALRM, SIGTERM, SIGKILL
from logging.handlers import TimedRotatingFileHandler
from daemon import Daemon
import lirc

from screen_manager import ScreenManager
import config

# OS enviroment variables for pitft
os.putenv ("SDL_VIDEODRIVER" , "fbcon")
os.environ["SDL_FBDEV"] = "/dev/fb1"
os.environ["SDL_MOUSEDEV"] = "/dev/input/touchscreen"
os.environ["SDL_MOUSEDRV"] = "TSLIB"

# Logger config
if not os.path.isdir (config.logpath):
	os.mkdir(config.logpath)

path = os.path.dirname(os.path.abspath(__file__)) + "/"

logger = logging.getLogger("PiTFT-Playerui")
try:
	if config.loglevel == "DEBUG":
		loglevel = logging.DEBUG
		logger.setLevel(loglevel)
		formatter = logging.Formatter("%(asctime)s %(levelname)-5s %(name)-32s %(lineno)-4d %(message)s")
	else:
		logger.setLevel(logging.INFO)
		formatter = logging.Formatter("%(asctime)s %(levelname)s %(message)s")
except:
	logger.setLevel(logging.INFO)

handler = TimedRotatingFileHandler(config.logpath + '/pitft-playerui.log',when="midnight",interval=1,backupCount=14)
handler.setFormatter(formatter)
logger.addHandler(handler)

## HAX FOR FREEZING ##
class Alarm(Exception):
	pass
def alarm_handler(signum, frame):
	logger.debug("ALARM")
	raise Alarm
## HAX END ##

def signal_term_handler(signal, frame):
    logger.debug('got SIGTERM')
    sys.exit(0)

class PitftDaemon(Daemon):
	sm = None
	screen = None

	# Setup Python game and Screen manager
	def setup(self):
		logger.info("Starting setup")

		signal(SIGTERM, signal_term_handler)
		# Python game ######################
		logger.info("Setting pygame")
		pygame_init_done = False
		while not pygame_init_done:
			try:
				pygame.init()
				pygame_init_done = True
			except:
				logger.debug("Pygame init failed")
				pygame_init_done = False
				time.sleep(5)

		pygame.mouse.set_visible(False)

		# Hax for freezing
		signal(SIGALRM, alarm_handler)
		alarm(3)
		try:
			# Set screen size
			size = width, height = config.resolution
			self.screen = pygame.display.set_mode(size)
			alarm(0)
		except Alarm:
			logger.debug("Keyboard interrupt?")
			raise KeyboardInterrupt
		# Hax end

		logger.info("Display driver: %s" % pygame.display.get_driver())

		# Screen manager ###############
		logger.info("Setting screen manager")
		self.sm = ScreenManager(path)
		logger.debug("Screen manager set")

		# LIRC
		lircrcfile = path + "pitft-playerui.lircrc"
		self.lirc_enabled = False
		if os.path.isfile(lircrcfile):
			try:
				self.lirc_sockid = lirc.init("pitft-playerui", lircrcfile, blocking=False)
				self.lirc_enabled = True
			except Exception, e:
				logger.debug(e)
				self.lirc_enabled = False
		
		# Mouse variables
		self.clicktime 	        = datetime.datetime.now()
		self.longpress_time     = timedelta(milliseconds=400)
		self.scroll_threshold   = 20
		self.start_pos          = 0,0
		self.mouse_scroll       = ""
		self.mousebutton_down   = False
		self.longpress          = False
		self.pos                = 0
		self.userevents 		= True

		# Times in milliseconds
		self.screen_refreshtime = 50
		self.player_refreshtime = 110
		self.sleeptime = self.screen_refreshtime / 2.0
	
		logger.debug("Setup done")

	def shutdown(self):
		# Close MPD connection -  TODO
#		self.pc.mpd.disconnect()
		pass

	# Main loop
	def run(self):
		self.setup()
		drawtime = datetime.datetime.now()
		refreshtime = datetime.datetime.now()

		while 1:
			# Check CLI and mouse events
			self.userevents = self.userevents | self.read_mouse()
			if self.lirc_enabled:
				self.userevents = self.userevents | self.read_lirc()
			
			# Refresh info
			if refreshtime < datetime.datetime.now():
				refreshtime = datetime.datetime.now() + timedelta(milliseconds=self.player_refreshtime)
				active = self.sm.refresh(self.userevents)
				self.userevents = False
				
			# Draw screen
			if drawtime < datetime.datetime.now():
				drawtime = datetime.datetime.now() + timedelta(milliseconds=self.screen_refreshtime)
					
				# Don't draw when display is off
				if active:
					self.sm.render(self.screen)
					pygame.display.flip()

	def read_mouse(self):
		direction = 0,0
		userevents = False
		
		for event in pygame.event.get():
			if event.type == pygame.MOUSEBUTTONDOWN:
				userevents = True
				self.clicktime = datetime.datetime.now()
				self.pos = self.start_pos = pygame.mouse.get_pos()

				# Instant click when backlight is off to wake
				if not self.sm.get_backlight_status():
					self.mousebutton_down = False
				else:
					self.mousebutton_down = True

			if event.type == pygame.MOUSEMOTION and self.mousebutton_down and not self.longpress:
				userevents = True
				pos = pygame.mouse.get_pos()
				direction = (pos[0] - self.pos[0], pos[1] - self.pos[1])

				# Start scrolling
				if not self.mouse_scroll:					
					if abs(direction[0]) >= self.scroll_threshold:
						self.mouse_scroll = "x"
						self.scroll(self.start_pos,direction[0],0)

					elif abs(direction[1]) >= self.scroll_threshold:
						self.mouse_scroll = "y"
						self.scroll(self.start_pos, 0, direction[1])

				# Scrolling already, update offset
				else:
					if self.mouse_scroll == "x" and abs(direction[0]) > 0:
						self.scroll(self.start_pos, direction[0], 0)
					if self.mouse_scroll == "y" and abs(direction[1]) > 0:
						self.scroll(self.start_pos, 0, direction[1])

				# Save new position
				self.pos = pos

			if event.type == pygame.MOUSEBUTTONUP:
				userevents = True
				if self.mousebutton_down and not self.longpress:
					# Not a long click or scroll: click
					if not self.mouse_scroll:
						self.sm.on_click(1, self.start_pos)
					else:
						self.scroll(self.start_pos, 0,0, True)

				# Clear variables
				self.mousebutton_down = False
				self.mouse_scroll     = ""
				self.longpress        = False

		# Long press - register second click
		if self.mousebutton_down and not self.mouse_scroll:
			userevents = True
			if datetime.datetime.now() - self.clicktime > self.longpress_time:
				self.mousebutton_down = self.sm.on_click(2, self.start_pos)

				# Update timers
				self.clicktime = datetime.datetime.now()
		return userevents

	def scroll(self, start, x, y, end=False):
		self.sm.on_scroll(start, x, y, end)

	def read_lirc(self):
		commands = lirc.nextcode()
		if commands:
			for command in commands:
				self.sm.pc.control_player(command)
				logger.debug("LIRC: %s" % command)
			return True
		return False


if __name__ == "__main__":
	daemon = PitftDaemon('/tmp/pitft-playerui-daemon.pid')
	if len(sys.argv) > 1:
		if 'start' == sys.argv[1]:
			daemon.start()
		elif 'stop' == sys.argv[1]:
			daemon.shutdown()
			daemon.stop()
		elif 'restart' == sys.argv[1]:
			daemon.restart()
		else:
			print "Unknown command"
			sys.exit(2)
		sys.exit(0)
	else:
		print "usage: %s start|stop|restart|" % sys.argv[0]
		print "usage: %s start|stop|restart|control <command>" % sys.argv[0]
		sys.exit(2)
