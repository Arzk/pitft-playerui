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
import pitft_ui
import config
import memcache

# OS enviroment variables for pitft
os.putenv ("SDL_VIDEODRIVER" , "fbcon")
os.environ["SDL_FBDEV"] = "/dev/fb1"
os.environ["SDL_MOUSEDEV"] = "/dev/input/touchscreen"
os.environ["SDL_MOUSEDRV"] = "TSLIB"

# Logging configs
if not os.path.isdir ('/var/log/pitft-playerui'):
	os.mkdir('/var/log/pitft-playerui')

logger = logging.getLogger("PiTFT-Playerui logger")
try: 
	if config.loglevel == "DEBUG":
		loglevel = logging.DEBUG
		logger.setLevel(loglevel)
	else:
		logger.setLevel(logging.INFO)
except:
	logger.setLevel(logging.INFO)
	
handler = TimedRotatingFileHandler('/var/log/pitft-playerui/pitft-playerui.log',when="midnight",interval=1,backupCount=14)
formatter = logging.Formatter("%(asctime)s %(levelname)s %(message)s")
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
		self.sm = pitft_ui.PitftPlayerui()

		# Mouse variables
		self.clicktime 	      = datetime.datetime.now()
		self.longpress_time   = timedelta(milliseconds=500)
		self.scroll_threshold = 20
		self.flip_threshold   = 80
		self.scroll_step      = 20
		self.start_x          = 0
		self.start_y          = 0
		self.mouse_scroll     = False
		self.mousebutton_down = False
		self.longpress        = False
		
		# Times in milliseconds
		self.screen_refreshtime = 100
		self.player_refreshtime = 500
		self.sleeptime = self.screen_refreshtime / 2.0

	def shutdown(self):
		# Close MPD connection -  TODO
#		self.sm.pc.mpd.disconnect()
		pass

	# Main loop
	def run(self):
		self.setup()

		try:
			drawtime = datetime.datetime.now()
			refreshtime = datetime.datetime.now()
			while 1:

				if refreshtime < datetime.datetime.now():
					refreshtime = datetime.datetime.now() + timedelta(milliseconds=self.player_refreshtime)
					# Refresh info
					self.sm.refresh()

				# Update screen
				if drawtime < datetime.datetime.now():
					drawtime = datetime.datetime.now() + timedelta(milliseconds=self.screen_refreshtime)
					# Don't draw when display is off
					if self.sm.get_backlight_status():
						self.sm.render(self.screen)
						pygame.display.flip()

					# Check CLI events
					self.read_cli()

					# Mouse events
					self.read_mouse()
				else:
					# Sleep a bit
					time.sleep(self.sleeptime/1000.0)
			
		except Exception, e:
			logger.debug(e)
			raise
			
	def read_mouse(self):
		for event in pygame.event.get():
			if event.type == pygame.MOUSEBUTTONDOWN:
				click_pos = (pygame.mouse.get_pos() [0], pygame.mouse.get_pos() [1])
				self.clicktime = datetime.datetime.now()

				# Instant click when backlight is off to turn it back on
				if not self.sm.get_backlight_status():
					click_pos = (pygame.mouse.get_pos() [0], pygame.mouse.get_pos() [1])
					self.sm.on_click(1, click_pos)

				else:
					# Save mouse position for determining if user has scrolled
					self.start_x,self.start_y = pygame.mouse.get_pos()
					self.mouse_scroll = False
					self.mousebutton_down = True

					#logger.debug("screen pressed") #for debugging purposes
					#pos = (pygame.mouse.get_pos() [0], pygame.mouse.get_pos() [1])
					#pygame.draw.circle(self.screen, (255,255,255), pos, 2, 0) #for debugging purposes - adds a small dot where the screen is pressed

			if event.type == pygame.MOUSEMOTION and self.mousebutton_down and not self.longpress:
				end_x, end_y = pygame.mouse.get_pos()
				direction_x = end_x - self.start_x
				direction_y = end_y - self.start_y

				if abs(direction_x) >= self.flip_threshold or abs(direction_y) >= self.scroll_threshold:
					self.mouse_scroll = True
					# Assume that the bigger amount of scroll (x vs y) was the intention
					if abs(direction_y) > abs(direction_x):
						# A vertical movement of 20 pixels scrolls one line
						if direction_y < 0:
							self.sm.inc_offset(int(floor(direction_y/self.scroll_step)))
						elif direction_y > 0:
							self.sm.inc_offset(int(ceil(direction_y/self.scroll_step)))
					else:
						# A horizontal flip switches next/prev
						if direction_x > 0:
							self.sm.button(6, 1)
						elif direction_x < 1:
							self.sm.button(8, 1)
						# don't repeat
						self.mousebutton_down = False

				# Save new position
				self.start_x,self.start_y=pygame.mouse.get_pos()

			if event.type == pygame.MOUSEBUTTONUP and self.mousebutton_down:
	
				# Not a long click or scroll
				if not self.longpress and not self.mouse_scroll:
					click_pos = (pygame.mouse.get_pos() [0], pygame.mouse.get_pos() [1])
					self.sm.on_click(1, click_pos)
					
				# Clear variables
				end_x = 0;
				end_y = 0;
				self.start_x = 0;
				self.start_y = 0;
				self.mouse_scroll = False
				self.mousebutton_down = False
				self.longpress = False

			# Long press - register second click
			elif self.mousebutton_down and not self.mouse_scroll:
				if datetime.datetime.now() - self.clicktime > self.longpress_time and not self.longpress:
					click_pos = (pygame.mouse.get_pos() [0], pygame.mouse.get_pos() [1])
					self.sm.on_click(2, click_pos)
					self.clicktime = datetime.datetime.now()
					self.longpress = True

				# Speed up the long press, if continued
				elif datetime.datetime.now() - self.clicktime > self.longpress_time/2 and self.longpress:
					click_pos = (pygame.mouse.get_pos() [0], pygame.mouse.get_pos() [1])
					self.sm.on_click(2, click_pos)
					self.clicktime = datetime.datetime.now()

			# Update screen timeout if there's any mouse activity
			if config.screen_timeout > 0 and not self.sm.backlight_forced_off:
				self.sm.update_screen_timeout()

	def read_cli(self):
		# See if there were any CLI commands
		shared = memcache.Client(['127.0.0.1:11211'], debug=0)    
		command = shared.get('command')
		if command:
			logger.debug("Got shared: %s" % command)
			self.sm.pc.control_player(command)
			
			# Set backlight on
			if not self.sm.backlight_forced_off:
				self.sm.update_screen_timeout()

			# Clear cache
			shared.set('command', None)

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
		elif 'control' == sys.argv[1] and len(sys.argv) == 3:
			daemon.control(sys.argv[2])
		else:
			print "Unknown command"
			sys.exit(2)
		sys.exit(0)
	else:
		print "usage: %s start|stop|restart|control <command>" % sys.argv[0]
		sys.exit(2)
