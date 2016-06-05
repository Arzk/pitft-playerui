# -*- coding: utf-8 -*-
import sys, pygame
from pygame.locals import *
import time
import subprocess
import os
import glob
import re
import pylast
import config
from mpd import MPDClient
from math import ceil, floor
import datetime
from datetime import timedelta
import pitft_ui
from signal import alarm, signal, SIGALRM, SIGTERM, SIGKILL
import logging
from logging.handlers import TimedRotatingFileHandler
from daemon import Daemon

# OS enviroment variables for pitft
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
	client = None
	network = None
	screen = None

	# Setup Python game, MPD, Last.fm and Screen manager
	def setup(self):
		logger.info("Starting setup")
		
		signal(SIGTERM, signal_term_handler)
		# Python game ######################
		logger.info("Setting pygame")
		pygame.init()
		pygame.mouse.set_visible(False)

		# Hax for freezing
		signal(SIGALRM, alarm_handler)
		alarm(3)
		try:
			# Set screen size
			size = width, height = 480, 320
			self.screen = pygame.display.set_mode(size)
			alarm(0)
		except Alarm:
			logger.debug("Keyboard interrupt?")
			raise KeyboardInterrupt
		# Hax end

		logger.info("Display driver: %s" % pygame.display.get_driver())

		# MPD ##############################
		logger.info("Setting MPDClient")
		self.client = MPDClient()
		self.client.timeout = 10
		self.client.idletimeout = None

		# Pylast ####################################################################  
		logger.info("Setting Pylast")
		username = config.username
		password_hash = pylast.md5(config.password_hash)
		self.network = pylast.LastFMNetwork(api_key = config.API_KEY, api_secret = config.API_SECRET)

		# Screen manager ###############
		logger.info("Setting screen manager")
		noSM = True
		while noSM:
			try:
				self.sm = pitft_ui.PitftPlayerui(self.client, self.network, logger)
				noSM = False
			except:
				noSM = True
				time.sleep(5)
#		except Exception, e:
#			logger.exception(e)
#			raise

		# Mouse variables
		self.longpress_time   =  timedelta(milliseconds=500)
		self.scroll_threshold = 20
		self.flip_threshold   = 80
		self.scroll_step      = 20
		self.start_x          = 0
		self.start_y          = 0
		self.mouse_scroll     = False
		self.mousebutton_down      = False
		self.longpress        = False

	# Connect to MPD server
	def connectToMPD(self):
		logger.info("Trying to connect MPD server")
		noConnection = True
		while noConnection:
			try:
				self.client.connect(config.mpd_host, config.mpd_port)
				noConnection=False
			except Exception, e:
				logger.info(e)
				noConnection=True
				time.sleep(15)
		logger.info("Connection to MPD server established.")

	# Click handler
	def on_click(self, mousebutton):
		click_pos = (pygame.mouse.get_pos() [0], pygame.mouse.get_pos() [1])

		# Screen is off and its touched
		if self.sm.get_backlight_status() == 0 and 0 <= click_pos[0] <= 480 and 0 <= click_pos[1] <= 320:
			logger.debug("Screen off, Screen touch")
			self.button(2, mousebutton)

		# Screen is on. Check which button is touched 
		else:
			# There is no multi touch so if one button is pressed another one can't be pressed at the same time

			# Selectors
			if 418 <= click_pos[0] <= 476 and 8 <= click_pos[1] <= 64:
				if config.spotify_host:
					logger.debug("Switching player")
					self.button(14, mousebutton)
			elif 418 <= click_pos[0] <= 476 and 66 <= click_pos[1] <= 122:
				logger.debug("Playlists")
				self.button(10, mousebutton)
			elif 418 <= click_pos[0] <= 476 and 124 <= click_pos[1] <= 180:
				if config.cdda_enabled:
					logger.debug("CD")
					self.button(11, mousebutton)
			elif 418 <= click_pos[0] <= 476 and 182 <= click_pos[1] <= 238:
				if config.radio_playlist:
					logger.debug("Radio")
					self.button(12, mousebutton)

			# Playlists are shown - hide on empty space click
			elif self.sm.get_playlists_status() or self.sm.get_playlist_status():
				if not 4 <= click_pos[0] <= 416 or not 4 <= click_pos[1] <= 243:
					logger.debug("Hiding lists")
					self.button(13, mousebutton)

				# List item clicked
				# List item to select: 4 - 33: 0, 34-63 = 1 etc
				elif 4 <= click_pos[0] <= 416 and 4 <= click_pos[1] <= 243:
					list_item = int(floor((click_pos[1] - 4)/30))
					if mousebutton == 1:
						logger.debug("Selecting list item %s" % list_item)
						self.sm.item_selector(list_item)
					elif mousebutton == 2:
						logger.debug("Second-clicked list item %s" % list_item)

			# Toggles
			elif 420 <= click_pos[0] <= 480 and 260 <= click_pos[1] <= 320:
				logger.debug("Screen off")
				self.button(2, mousebutton)
			elif 315 <= click_pos[0] <= 377 and 56 <= click_pos[1] <= 81:
				logger.debug("Toggle repeat") 
				self.button(0, mousebutton)
			elif 315 <= click_pos[0] <= 377 and 88 <= click_pos[1] <= 113:
				logger.debug("Toggle random")
				self.button(1, mousebutton)

			# Volume
			elif 258 <= click_pos[0] <= 316 and 190 <= click_pos[1] <= 248:
					if config.volume_enabled:
						logger.debug("Volume-")
						self.button(3, mousebutton)
			elif 354 <= click_pos[0] <= 412 and 190 <= click_pos[1] <=248:
					if config.volume_enabled:
						logger.debug("Volume+")
						self.button(4, mousebutton)

			# Controls
			elif 258 <= click_pos[0] <= 294 and 132 <= click_pos[1] <= 180:
				logger.debug("Prev")
				self.button(6, mousebutton)
			elif 296 <= click_pos[0] <= 352 and 132 <= click_pos[1] <= 180:
				logger.debug("Toggle play/pause")
				self.button(7, mousebutton)
			elif 354 <= click_pos[0] <= 410 and 132 <= click_pos[1] <= 180:
				logger.debug("Next")
				self.button(8, mousebutton) 

			# Open playlist when longpressing on bottom
			elif 244 <= click_pos[1] <= 320 and mousebutton == 2:
				if self.sm.get_active_player() == "mpd":
					logger.debug("Toggle playlist")
					self.button(9, mousebutton)

	#define action on pressing buttons
	def button(self, number, mousebutton):
		if mousebutton == 1:
			logger.debug("You pressed button %s" % number)

			if number == 0:  
				self.sm.toggle_repeat()

			elif number == 1:
				self.sm.toggle_random()

			elif number == 2:
				self.sm.toggle_backlight()

			elif number == 3:
				self.sm.set_volume(1, "-")

			elif number == 4:
				self.sm.set_volume(1, "+")

			elif number == 5:
				self.sm.control_player("stop")

			elif number == 6:
				self.sm.control_player("previous")

			elif number == 7:
				self.sm.toggle_playback()

			elif number == 8:
				self.sm.control_player("next")

			elif number == 10:
				self.sm.toggle_playlists()

			elif number == 11:
				self.sm.play_cd()

			elif number == 12:
				if not self.sm.get_playlist_status():
					self.sm.load_playlist(config.radio_playlist)
					self.sm.toggle_playlist("True")
				else:
					self.sm.toggle_playlist("False")
	
			elif number == 13:
				self.sm.toggle_playlists("False")
				self.sm.toggle_playlist("False")

			elif number == 14:
				self.sm.switch_active_player("toggle")
		elif mousebutton == 2:
			logger.debug("You longpressed button %s" % number)

			if number == 3:
				self.sm.set_volume(10, "-")

			elif number == 4:
				self.sm.set_volume(10, "+")

			elif number == 6:
				self.sm.control_player("rwd")

			elif number == 8:
				self.sm.control_player("ff")

			elif number == 9:
				self.sm.toggle_playlist()

		else:
			logger.debug("mouse button %s not supported" % mousebutton)

	def shutdown(self):
		# Close MPD connection
		if self.client:
			self.client.close()
			self.client.disconnect()
		
	# Main loop
	def run(self):
		self.setup()
		self.connectToMPD()

		try:
			drawtime = datetime.datetime.now()
			while 1:
				for event in pygame.event.get():
					if event.type == pygame.MOUSEBUTTONDOWN:
					
						# Instant click when backlight is off to turn it back on
						if self.sm.get_backlight_status() == 0:
							self.on_click(1)

						else:
							# Save mouse position for determining if user has scrolled
							self.start_x,self.start_y = pygame.mouse.get_pos()
							self.mouse_scroll = False
							clicktime = datetime.datetime.now()
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
									self.button(6, 1)
								elif direction_x < 1:
									self.button(8, 1)
								# don't repeat
								self.mousebutton_down = False
	
						# Save new position
						self.start_x,self.start_y=pygame.mouse.get_pos()

					if event.type == pygame.MOUSEBUTTONUP and self.mousebutton_down:
						# Not a long click or scroll
						if not self.longpress and not self.mouse_scroll:
							self.on_click(1)
							
						# Clear variables
						end_x = 0;
						end_y = 0;
						self.start_x = 0;
						self.start_y = 0;
						self.mouse_scroll = False
						self.mousebutton_down = False
						self.longpress = False

					# Long press - register second click
					elif self.mousebutton_down and datetime.datetime.now() - clicktime > self.longpress_time and not self.mouse_scroll and not self.longpress:
						self.on_click(2)
						clicktime = datetime.datetime.now()
						self.longpress = True

					# Speed up the long press, if continued
					elif self.mousebutton_down and datetime.datetime.now() - clicktime > self.longpress_time/2 and not self.mouse_scroll and self.longpress:
						self.on_click(2)
						clicktime = datetime.datetime.now()
					
					# Update screen timeout if there's any mouse activity
					if config.screen_timeout > 0:
						self.sm.updateScreenTimeout()

				# Update screen, fps=20
				if drawtime < datetime.datetime.now():
					drawtime = datetime.datetime.now() + timedelta(milliseconds=50)
					self.sm.refresh_players()
					self.sm.parse_song()
					self.sm.render(self.screen)
					pygame.display.flip()
			pygame.display.update()
		except Exception, e:
			logger.debug(e)
			raise

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
		print "usage: %s start|stop|restart" % sys.argv[0]
		sys.exit(2)
