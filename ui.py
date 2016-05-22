# -*- coding: utf-8 -*-
import sys, pygame
from pygame.locals import *
import time
import subprocess
import os
import glob
import re
import pylast
import lastfm_login
from mpd import MPDClient
from math import ceil
import const
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
logger = logging.getLogger("PiTFT-Playerui logger")
logger.setLevel(logging.DEBUG)
#logger.setLevel(logging.INFO)

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
		username = lastfm_login.username
		password_hash = lastfm_login.password_hash
		self.network = pylast.LastFMNetwork(api_key = lastfm_login.API_KEY, api_secret = lastfm_login.API_SECRET)

		# Screen manager ###############
		logger.info("Setting screen manager")
		try:
			self.sm = pitft_ui.PitftPlayerui(self.client, self.network, logger)
		except Exception, e:
			logger.exception(e)
			raise

	# Connect to MPD server
	def connectToMPD(self):
		logger.info("Trying to connect MPD server")
		noConnection = True
		while noConnection:
			try:
				self.client.connect("localhost", 6600)
				noConnection=False
			except Exception, e:
				logger.info(e)
				noConnection=True
		logger.info("Connection to MPD server established.")

	# Click handler
	def on_click(self):
		click_pos = (pygame.mouse.get_pos() [0], pygame.mouse.get_pos() [1])

		# Screen is off and its touched
		if self.sm.get_backlight_status() == 0 and 0 <= click_pos[0] <= 480 and 0 <= click_pos[1] <= 320:
			logger.debug("Screen off, Screen touch")
			self.button(9)

		# Screen is on. Check which button is touched 
		else:
			# There is no multi touch so if one button is pressed another one can't be pressed at the same time
			# Selectors

			# Spotify button
			if 418 <= click_pos[0] <= 476 and 8 <= click_pos[1] <= 64:
				if self.sm.get_active_player() == "spotify":
					logger.debug("Switching to MPD")
				else:
					logger.debug("Switching to Spotify")
				self.button(14)
			# Playlists button
			if 418 <= click_pos[0] <= 476 and 66 <= click_pos[1] <= 122:
				logger.debug("Playlists")
				self.button(10)
			# CD button
			elif 418 <= click_pos[0] <= 476 and 124 <= click_pos[1] <= 180:
				logger.debug("CD")
				self.button(11)
			# Radio button
			elif 418 <= click_pos[0] <= 476 and 182 <= click_pos[1] <= 238:
				logger.debug("Radio")
				self.button(12)

			# Playlists are shown - hide on empty space click
			elif self.sm.get_playlists_status() or self.sm.get_playlist_status():
				if not 4 <= click_pos[0] <= 416 or not 12 <= click_pos[1] <= 232:
					logger.debug("Hiding playlists view")
					self.button(13)
				elif 4 <= click_pos[0] <= 416 and 12 <= click_pos[1] <= 42:
					logger.debug("Selecting list item 0")
					self.sm.item_selector(0)
				elif 4 <= click_pos[0] <= 416 and 42 <= click_pos[1] <= 72:
					logger.debug("Selecting list item 1")
					self.sm.item_selector(1)
				elif 4 <= click_pos[0] <= 416 and 72 <= click_pos[1] <= 112:
					logger.debug("Selecting list item 2")
					self.sm.item_selector(2)
				elif 4 <= click_pos[0] <= 416 and 112 <= click_pos[1] <= 142:
					logger.debug("Selecting list item 3")
					self.sm.item_selector(3)
				elif 4 <= click_pos[0] <= 416 and 142 <= click_pos[1] <= 172:
					logger.debug("Selecting list item 4")
					self.sm.item_selector(4)
				elif 4 <= click_pos[0] <= 416 and 172 <= click_pos[1] <= 202:
					logger.debug("Selecting list item 5")
					self.sm.item_selector(5)
				elif 4 <= click_pos[0] <= 416 and 202 <= click_pos[1] <= 232:
					logger.debug("Selecting list item 6")
					self.sm.item_selector(6)

			# Toggles
			elif 420 <= click_pos[0] <= 480 and 260 <= click_pos[1] <=320:
				logger.debug("Screen off")
				self.button(9)
			elif 315 <= click_pos[0] <= 557 and 56 <= click_pos[1] <=81:
				logger.debug("Toggle repeat") 
				self.button(0)
			elif 315 <= click_pos[0] <= 557 and 88 <= click_pos[1] <=113:
				logger.debug("Toggle random")
				self.button(1)	
			# Controls
			elif 242 <= click_pos[0] <= 298 and 132 <= click_pos[1] <=180:
				logger.debug("Prev")
				self.button(6)
			elif 300 <= click_pos[0] <= 356 and 132 <= click_pos[1] <=180:
				logger.debug("Toggle play/pause")
				self.button(7)
			elif 358 <= click_pos[0] <= 414 and 132 <= click_pos[1] <=180:
				logger.debug("Next")
				self.button(8) 

	#define action on pressing buttons
	def button(self, number):
		logger.debug("You pressed button %s" % number)
		if number == 0:    #specific script when exiting
			self.sm.toggle_repeat()

		elif number == 1:
			self.sm.toggle_random()

		elif number == 5:
			self.sm.control_player("stop")

		elif number == 6:
			self.sm.control_player("previous")

		elif number == 7:
			self.sm.toggle_playback()

		elif number == 8:
			self.sm.control_player("next")

		elif number == 9:
			self.sm.toggle_backlight()

		elif number == 10:
			self.sm.toggle_playlists()

		elif number == 11:
			self.sm.play_cd()

		elif number == 12:
			if not self.sm.get_playlist_status():
				self.sm.load_playlist("Radio")
				self.sm.toggle_playlist("True")
			else:
				self.sm.toggle_playlist("False")
	
		elif number == 13:
			self.sm.toggle_playlists("False")
			self.sm.toggle_playlist("False")

		elif number == 14:
			self.sm.switch_active_player("toggle")

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
						#logger.debug("screen pressed") #for debugging purposes
						#pos = (pygame.mouse.get_pos() [0], pygame.mouse.get_pos() [1])
						#pygame.draw.circle(self.screen, (255,255,255), pos, 2, 0) #for debugging purposes - adds a small dot where the screen is pressed
						self.on_click()
						

				# Update screen, fps=10
				if drawtime < datetime.datetime.now():
					drawtime = datetime.datetime.now() + timedelta(milliseconds=20)
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
	if len(sys.argv) == 2:
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
		print "usage: %s start|stop|restart" % sys.argv[0]
		sys.exit(2)
