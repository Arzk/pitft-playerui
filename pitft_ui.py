# -*- coding: utf-8 -*-
import sys, pygame
from pygame.locals import *
import time
import logging
import subprocess
import os
import glob
import re
import pylast
from math import ceil, floor
from threading import Thread
import datetime
from datetime import timedelta
import config
import control

class PitftPlayerui:
	def __init__(self):

		self.logger = logging.getLogger("PiTFT-Playerui logger.screen manager")
		self.pc = control.PlayerControl()

		# Pylast  
		self.lastfm_connected = False
		
		# Paths
		self.path = os.path.dirname(sys.argv[0]) + "/"
		os.chdir(self.path)

		# Threads
		self.coverartThread = None
		self.oldCoverartThreadRunning = False
	
		# Fonts
		self.fontfile = self.path + config.fontfile
		self.logger.debug("Font file: %s" % self.fontfile)
		self.font = {}
		self.font['details']	= pygame.font.Font(self.fontfile, 16)
		self.font['elapsed']	= pygame.font.Font(self.fontfile, 16)
		self.font['playlist']	= pygame.font.Font(self.fontfile, 20)
		self.font['field']		= pygame.font.Font(self.fontfile, 20)

		# Images
		self.image = {}
		self.image["background"]			=pygame.image.load(self.path + "pics/" + "background.png")
		self.image["coverart_place"]		=pygame.image.load(self.path + "pics/" + "coverart-placer.png")
		self.image["coverart_border"]		=pygame.image.load(self.path + "pics/" + "coverart-border.png")
		self.image["details"]				=pygame.image.load(self.path + "pics/" + "details.png")
		self.image["field"]					=pygame.image.load(self.path + "pics/" + "field-value.png")
		self.image["position_bg"]			=pygame.image.load(self.path + "pics/" + "position-background.png")
		self.image["position_fg"]			=pygame.image.load(self.path + "pics/" + "position-foreground.png")
		self.image["icon_randomandrepeat"]	=pygame.image.load(self.path + "pics/" + "randomandrepeat.png")
		self.image["icon_screenoff"]		=pygame.image.load(self.path + "pics/" + "screen-off.png")
	
		## Buttons
		self.image["button_next"]			=pygame.image.load(self.path + "pics/" + "button-next.png")
		self.image["button_pause"]			=pygame.image.load(self.path + "pics/" + "button-pause.png")
		self.image["button_play"]			=pygame.image.load(self.path + "pics/" + "button-play.png")
		self.image["button_stop"]			=pygame.image.load(self.path + "pics/" + "button-stop.png")
		self.image["button_prev"]			=pygame.image.load(self.path + "pics/" + "button-prev.png")
		self.image["button_volumeminus"]	=pygame.image.load(self.path + "pics/" + "button-volumeminus.png")
		self.image["button_volumeplus"]		=pygame.image.load(self.path + "pics/" + "button-volumeplus.png")
		self.image["button_toggle_off"]		=pygame.image.load(self.path + "pics/" + "toggle-off.png")
		self.image["button_toggle_on"]		=pygame.image.load(self.path + "pics/" + "toggle-on.png")
		self.image["button_spotify"]		=pygame.image.load(self.path + "pics/" + "button-spotify.png")
		self.image["button_mpd"]			=pygame.image.load(self.path + "pics/" + "button-mpd.png")
		self.image["button_radio"]			=pygame.image.load(self.path + "pics/" + "button-radio.png")
		self.image["button_cd"]				=pygame.image.load(self.path + "pics/" + "button-cd.png")
		self.image["button_playlists"]		=pygame.image.load(self.path + "pics/" + "button-playlists.png")
		self.image["button_playlist"]		=pygame.image.load(self.path + "pics/" + "button-list.png")

		# Things to remember
		self.screen_timeout_time = 0
		self.processingCover = False
		self.coverFetched = False
		self.playlist = {}
		self.playlists = {}

		# What to update
		self.updateTrackInfo = False
		self.updateAlbum	 = False	
		self.updateElapsed	 = False
		self.updateRandom	 = False
		self.updateRepeat	 = False
		self.updateVolume	 = False
		self.updateState	 = False
		self.updateAll		 = True

		# Things to show
		self.trackfile = None
		self.artist = ""
		self.album = ""
		self.date = ""
		self.track = ""
		self.title = ""
		self.file = ""
		self.timeElapsed = "00:00"
		self.timeTotal = "00:00"
		self.timeElapsedPercentage = 0
		self.playbackStatus = "stop"
		self.volume = 0
		self.random = 0
		self.repeat = 0
		self.cover = False

		# Alternative views
		self.showPlaylist	 = False
		self.showPlaylists	 = False

		# Offset for list scrolling
		self.offset = 0

		# Turn backlight on
		self.turn_backlight_on()
		
	def connect_lfm(self):
		self.logger.info("Setting Pylast")
		username = config.username
		password_hash = pylast.md5(config.password_hash)
		self.lastfm_connected = False
		try:
			self.lfm = pylast.LastFMNetwork(api_key = config.API_KEY, api_secret = config.API_SECRET)
			self.lastfm_connected = True
			self.logger.debug("Connected to Last.fm")
		except:
			self.lfm = ""
			time.sleep(5)
			self.logger.debug("Last.fm not connected")

	def parse_song(self):

		# -------------
		# |  PARSE    |
		# -------------
		
		# Artist
		try:
			artist = self.pc.song["artist"].decode('utf-8')
		except:
			artist = ""

		# Album
		try:
			album = self.pc.song["album"].decode('utf-8')
		except:
			album = ""
		# Album Date
		try:
			date = self.pc.song["date"].decode('utf-8')
		except:
			date = ""
		# Track Number
		try:
			track = self.pc.song["track"].decode('utf-8')
		except:
			track = ""
		# Track Title
		try:
			if self.pc.song["title"]:
				title = self.pc.song["title"].decode('utf-8')
			else:
				title = self.pc.song["file"].decode('utf-8')
		except:
			title = ""
	
		# Time elapsed
		try:
			min = int(ceil(float(self.pc.status["elapsed"])))/60
			min = min if min > 9 else "0%s" % min
			sec = int(ceil(float(self.pc.status["elapsed"])%60))
			sec = sec if sec > 9 else "0%s" % sec
			timeElapsed = "%s:%s" % (min,sec)
		except:
			timeElapsed = "00:00"

		# Time total
		try:
			min = int(ceil(float(self.pc.song["time"])))/60
			sec = int(ceil(float(self.pc.song["time"])%60))
			min = min if min > 9 else "0%s" % min
			sec = sec if sec > 9 else "0%s" % sec
			timeTotal = "%s:%s" % (min,sec)
		except:
			timeTotal = "00:00"

		# Time elapsed percentage
		try:
			timeElapsedPercentage = float(self.pc.status["elapsed"])/float(self.pc.song["time"])
		except:
			timeElapsedPercentage = 0

		# Playback status
		try:
			playbackStatus = self.pc.status["state"]
		except:
			playbackStatus = "stop"

		# Repeat
		try:
			repeat = int(self.pc.status["repeat"])
		except:
			repeat = 0

		# Random
		try:
			random = int(self.pc.status["random"])
		except:
			random = 0

		# Volume
		try:
			volume = int(self.pc.status["volume"])
		except:
			volume = 0

		# -------------
		# |  CHANGES  |
		# -------------

		# Artist
		if self.artist != artist:
			self.logger.debug("Artist if")
			self.artist = artist
			self.updateTrackInfo = True

		# Album
		if self.album != album or self.oldCoverartThreadRunning:
			self.logger.debug("Album if")
			self.album = album
			self.updateAlbum = True
			self.cover = False
			
			# Find cover art on different thread			
			try:
				if self.coverartThread:
					self.logger.debug("if caT")
					if self.coverartThread.is_alive():
						self.logger.debug("caT is alive")
						self.oldCoverartThreadRunning = True
					else:
						self.logger.debug("caT not live")
						self.oldCoverartThreadRunning = False
						self.coverartThread = Thread(target=self.fetch_coverart)
						self.logger.debug("caT go")
						self.coverartThread.start()
				else:
					self.logger.debug("not caT")
					self.coverartThread = Thread(target=self.fetch_coverart)
					self.coverartThread.start()
			except Exception, e:
				self.logger.debug("Coverartthread: %s" % e)
				self.processingCover = False

		# Album Date
		if self.date != date:
			self.date = date
			self.updateTrackInfo = True

		# Track Number
		if self.track != track:
			self.track = track
			self.updateTrackInfo = True

		# Track Title
		if self.title != title:
			self.title = title
			self.updateTrackInfo = True

		# Time elapsed
		if self.timeElapsed != timeElapsed:
			self.timeElapsed = timeElapsed
			self.updateElapsed = True

		# Time total
		if self.timeTotal != timeTotal:
			self.timeTotal = timeTotal
			self.updateTrackInfo = True
			self.updateElapsed = True

		# Time elapsed percentage
		if self.timeElapsedPercentage != timeElapsedPercentage:
			self.timeElapsedPercentage = timeElapsedPercentage
			self.updateElapsed = True

		# Playback status
		if self.playbackStatus != playbackStatus:
			self.playbackStatus = playbackStatus
			self.updateState = True

		# Repeat
		if self.repeat != repeat:
			self.repeat = repeat
			self.updateRepeat = True

		# Random
		if self.random != random:
			self.random = random
			self.updateRandom = True

		# Volume
		if self.volume != volume:
			self.volume = volume
			self.updateVolume = True
			
	def render(self, surface):
	
		# Connect to last.fm
		if not self.lastfm_connected and config.API_KEY and config.API_SECRET:
			self.connect_lfm()

		# Refresh information from players
		self.pc.refresh_players()

		# Parse new song information
		self.parse_song()
		
		if self.updateAll:
			self.updateTrackInfo = True
			self.updateAlbum	 = True
			self.updateElapsed	 = True
			self.updateRandom	 = True
			self.updateRepeat	 = True
			self.updateVolume	 = True
			self.updateState	 = True
			
			surface.blit(self.image["background"], (0,0))	
			surface.blit(self.image["coverart_place"],(4,4))
			surface.blit(self.image["details"], (6, 263))
			surface.blit(self.image["icon_randomandrepeat"], (285, 60))
			surface.blit(self.image["position_bg"], (55, 245))
			surface.blit(self.image["button_prev"], (258, 132))
			surface.blit(self.image["button_next"], (354, 132))
			
			if config.volume_enabled:
				surface.blit(self.image["button_volumeminus"], (258, 190))
				surface.blit(self.image["button_volumeplus"], (354, 190))
				
			surface.blit(self.image["icon_screenoff"], (460, 304))

			# Change player button, if more than 1 player available
			if self.pc.get_active_player() == "spotify" and self.pc.mpd:
				surface.blit(self.image["button_spotify"], (418, 8))
			elif self.pc.get_active_player() == "mpd" and self.pc.spotify:
				surface.blit(self.image["button_mpd"], (418, 8))
					
			if self.pc.mpd:
				surface.blit(self.image["button_playlists"], (418, 66))
			
			if self.pc.mpd and config.cdda_enabled:
				surface.blit(self.image["button_cd"], (418, 124))
			
			if self.pc.mpd and config.radio_playlist:
				surface.blit(self.image["button_radio"], (418, 182))

		if self.updateAlbum or self.coverFetched:
			if self.cover:
				surface.blit(self.image["cover"], (4,4))
				surface.blit(self.image["coverart_border"],(4,4))
				self.coverFetched = False
			else:
				# Reset background
				surface.blit(self.image["coverart_place"],(4,4))
			
		if self.updateTrackInfo:
			if not self.updateAll:
				surface.blit(self.image["background"], (0,231), (0,231, 480,89)) # reset background
				surface.blit(self.image["details"], (6, 263))
				surface.blit(self.image["position_bg"], (55, 245))
				surface.blit(self.image["icon_screenoff"], (460, 304))	# redraw screenoff icon

			text = self.font["details"].render(self.artist, 1,(230,228,227))
			surface.blit(text, (60, 258)) # Artist
			if self.date:
				text = self.font["details"].render(self.album + " (" + self.date + ")", 1,(230,228,227))
			else:
				text = self.font["details"].render(self.album, 1,(230,228,227))
			surface.blit(text, (60, 278)) # Album
			if self.track:
				text = self.font["details"].render(self.track.zfill(2) + " - " + self.title, 1,(230,228,227))
			else:
				text = self.font["details"].render(self.title, 1,(230,228,227))
			surface.blit(text, (60, 298)) # Title
			if self.pc.get_active_player() == "mpd":
				text = self.font["elapsed"].render(self.timeTotal, 1,(230,228,227))
				surface.blit(text, (429, 238)) # Track length

		# Spotify-connect-web api doesn't deliver elapsed information
		if self.updateElapsed and self.pc.get_active_player() == "mpd":
			if not self.updateAll or not self.updateTrackInfo:
				surface.blit(self.image["background"], (0,242), (0,242, 427,20)) # reset background
				surface.blit(self.image["position_bg"], (55, 245))
			surface.blit(self.image["position_fg"], (55, 245),(0,0,int(370*self.timeElapsedPercentage),10))
			text = self.font["elapsed"].render(self.timeElapsed, 1,(230,228,227))
			surface.blit(text, (10, 238)) # Elapsed

		if self.updateRepeat:
			if not self.updateAll:
				surface.blit(self.image["background"], (310,50), (310,50, 105,31)) # reset background

			if self.repeat == 1:
				surface.blit(self.image["button_toggle_on"], (313,56))
			else:
				surface.blit(self.image["button_toggle_off"], (313,56))

		if self.updateRandom:
			if not self.updateAll:
				surface.blit(self.image["background"], (310,83), (310,83, 105,31)) # reset background

			if self.random == 1:
				surface.blit(self.image["button_toggle_on"], (313,88))
			else:
				surface.blit(self.image["button_toggle_off"], (313,88))

		if self.updateVolume:
			if config.volume_enabled:
				if not self.updateAll:
					surface.blit(self.image["field"], (303, 196), (2,2, 46,26)) # Reset field value area
				else:
					surface.blit(self.image["field"], (303, 196)) # Draw field
			
				text = self.font["field"].render(str(self.volume), 1,(230,228,227))

				pos = 304 + (48 - text.get_width())/2
				surface.blit(text, (pos, 199)) # Volume
				
		if self.updateState:
			if not self.updateAll:
				surface.blit(self.image["background"], (304,130), (304,130, 50,50)) # reset background
			if self.playbackStatus == "play":
				surface.blit(self.image["button_pause"], (306, 132))			
			else:
				surface.blit(self.image["button_play"], (306, 132))

		if self.showPlaylist:
			surface.blit(self.image["background"], (4,4), (4,4, 416,234)) # reset background
			if self.playlist:
				for i in range(0,8):
					try:
						playlistitem = self.playlist[i+self.offset]
						if "title" in playlistitem:
							if "artist" in playlistitem:
								playlistitem = playlistitem["artist"] + " - " + playlistitem["title"]
							else:
								playlistitem = playlistitem["title"]
						if "file" in playlistitem:
							playlistitem = playlistitem["file"].split("/")[-1]
					except:
						playlistitem = ""
					text = self.font["playlist"].render(playlistitem, 1,(230,228,227))
					surface.blit(text, (12, 4 + 30*int(i)),(0,0, 408,30))

		if self.showPlaylists:
			surface.blit(self.image["background"], (4,4), (4,4, 416,234)) # reset background
			if self.playlists:
				for i in range(0,8):
					try:
						listitem = self.playlists[i+self.offset]["playlist"]
					except:
						listitem = ""
					text = self.font["playlist"].render(listitem, 1,(230,228,227))
					surface.blit(text, (12, 4 + 30*int(i)),(0,0, 408,30))

		# Something is playing - update screen timeout
		if self.pc.status and config.screen_timeout > 0:
			if self.pc.status["state"] == "play": 
				self.update_screen_timeout()
				if not self.get_backlight_status():
					self.turn_backlight_on()
		
			# Nothing playing for 5 seconds, turn off screen if not already off
			elif self.screen_timeout_time < datetime.datetime.now() and self.backlight:
				self.turn_backlight_off()
		
		# Reset updates
		self.resetUpdates()

	# Click handler
	def on_click(self, mousebutton, click_pos):

		# Screen is off and its touched
		if self.get_backlight_status() == 0 and 0 <= click_pos[0] <= 480 and 0 <= click_pos[1] <= 320:
			self.logger.debug("Screen off, Screen touch")
			self.button(2, mousebutton)

		# Screen is on. Check which button is touched 
		else:
			# There is no multi touch so if one button is pressed another one can't be pressed at the same time

			# Selectors
			if 418 <= click_pos[0] <= 476 and 8 <= click_pos[1] <= 64:
				if self.pc.mpd and self.pc.spotify:
					self.logger.debug("Switching player")
					self.button(14, mousebutton)
			elif 418 <= click_pos[0] <= 476 and 66 <= click_pos[1] <= 122:
				if self.pc.mpd:
					self.logger.debug("Playlists")
					self.button(10, mousebutton)
			elif 418 <= click_pos[0] <= 476 and 124 <= click_pos[1] <= 180:
				if self.pc.mpd and config.cdda_enabled:
					self.logger.debug("CD")
					self.button(11, mousebutton)
			elif 418 <= click_pos[0] <= 476 and 182 <= click_pos[1] <= 238:
				if self.pc.mpd and config.radio_playlist:
					self.logger.debug("Radio")
					self.button(12, mousebutton)

			# Playlists are shown - hide on empty space click
			elif self.get_playlists_status() or self.get_playlist_status():
				if not 4 <= click_pos[0] <= 416 or not 4 <= click_pos[1] <= 243:
					self.logger.debug("Hiding lists")
					self.button(13, mousebutton)

				# List item clicked
				# List item to select: 4 - 33: 0, 34-63 = 1 etc
				elif 4 <= click_pos[0] <= 416 and 4 <= click_pos[1] <= 243:
					list_item = int(floor((click_pos[1] - 4)/30))
					if mousebutton == 1:
						self.logger.debug("Selecting list item %s" % list_item)
						self.item_selector(list_item)
					elif mousebutton == 2:
						self.logger.debug("Second-clicked list item %s" % list_item)

			# Toggles
			elif 420 <= click_pos[0] <= 480 and 260 <= click_pos[1] <= 320:
				self.logger.debug("Screen off")
				self.button(2, mousebutton)
			elif 315 <= click_pos[0] <= 377 and 56 <= click_pos[1] <= 81:
				self.logger.debug("Toggle repeat") 
				self.button(0, mousebutton)
			elif 315 <= click_pos[0] <= 377 and 88 <= click_pos[1] <= 113:
				self.logger.debug("Toggle random")
				self.button(1, mousebutton)

			# Volume
			elif 258 <= click_pos[0] <= 316 and 190 <= click_pos[1] <= 248:
					if config.volume_enabled:
						self.logger.debug("Volume-")
						self.button(3, mousebutton)
			elif 354 <= click_pos[0] <= 412 and 190 <= click_pos[1] <=248:
					if config.volume_enabled:
						self.logger.debug("Volume+")
						self.button(4, mousebutton)

			# Controls
			elif 258 <= click_pos[0] <= 294 and 132 <= click_pos[1] <= 180:
				self.logger.debug("Prev")
				self.button(6, mousebutton)
			elif 296 <= click_pos[0] <= 352 and 132 <= click_pos[1] <= 180:
				self.logger.debug("Toggle play/pause")
				self.button(7, mousebutton)
			elif 354 <= click_pos[0] <= 410 and 132 <= click_pos[1] <= 180:
				self.logger.debug("Next")
				self.button(8, mousebutton) 

			# Open playlist when longpressing on bottom
			elif 244 <= click_pos[1] <= 320 and mousebutton == 2:
				if self.pc.mpd and self.pc.get_active_player() == "mpd":
					self.logger.debug("Toggle playlist")
					self.button(9, mousebutton)

	#define action on pressing buttons
	def button(self, number, mousebutton):
		if mousebutton == 1:
			self.logger.debug("You pressed button %s" % number)

			if number == 0:  
				self.pc.control_player("repeat")

			elif number == 1:
				self.pc.control_player("random")

			elif number == 2:
				self.toggle_backlight()

			elif number == 3:
				self.pc.set_volume(1, "-")
				
			elif number == 4:
				self.pc.set_volume(1, "+")

			elif number == 5:
				self.pc.control_player("stop")

			elif number == 6:
				self.pc.control_player("previous")
				self.pc.listen_test()
			elif number == 7:
				self.pc.control_player("play_pause")

			elif number == 8:
				self.pc.control_player("next")

			elif number == 10:
				self.toggle_playlists()

			elif number == 11:
				self.pc.control_player("cd")
				self.update_all()

			elif number == 12:
				if not self.get_playlist_status():
					self.pc.control_player("radio")
					self.toggle_playlist("True")
				else:
					self.toggle_playlist("False")
	
			elif number == 13:
				self.toggle_playlists("False")
				self.toggle_playlist("False")

			elif number == 14:
				self.pc.control_player("switch_player")
				self.update_all()
				
		elif mousebutton == 2:
			self.logger.debug("You longpressed button %s" % number)

			if number == 3:
				self.pc.set_volume(10, "-")

			elif number == 4:
				self.pc.set_volume(10, "+")

			elif number == 6:
				self.pc.control_player("rwd")

			elif number == 8:
				self.pc.control_player("ff")

			elif number == 9:
				self.toggle_playlist()

		else:
			self.logger.debug("mouse button %s not supported" % mousebutton)

	def fetch_coverart(self):
		self.logger.debug("caT start")
		self.processingCover = True
		self.coverFetched = False
		self.cover = False

		# Search for local coverart
		if "file" in self.pc.song and self.pc.get_active_player() == "mpd" and config.library_path:
		
			folder = os.path.dirname(config.library_path + "/" + self.pc.song["file"])
			coverartfile = ""
			
			# Get all folder.* files from album folder
			coverartfiles = glob.glob(folder + '/folder.*')

			if coverartfiles:
				self.logger.debug("Found coverart files: %s" % coverartfiles)
				# If multiple found, select one of them
				for file in coverartfiles:
					# Check file extension, png, jpg and gif accepted
					if file.lower().endswith(('.png', '.jpg', '.jpeg', '.gif')):
						if not coverartfile:
							coverartfile = file
							self.logger.debug("Set first candidate for coverart: %s" % coverartfile)
						else:
							# Found multiple files. Assume that the largest one has the best quality
							if os.path.getsize(coverartfile) < os.path.getsize(file):
								coverartfile = file
								self.logger.debug("Better candidate found: %s" % coverartfile)
				if coverartfile:
					# Image found, load it
					self.logger.debug("Using coverart: %s" % coverartfile)
					coverart=pygame.image.load(coverartfile)
					self.image["cover"] = pygame.transform.scale(coverart, (228, 228))
					self.processingCover = False
					self.coverFetched = True
					self.cover = True
				else:
					self.logger.debug("No local coverart file found, switching to Last.FM")				

		# Check Spotify coverart
		elif "cover_uri" in self.pc.song and self.pc.get_active_player() == "spotify" and self.pc.spotify:
			try:
				coverart_url = config.spotify_host + ":" + config.spotify_port + "/api/info/image_url/" + self.pc.song["cover_uri"]
				if coverart_url:
					subprocess.check_output("wget -q %s -O %s/cover.png" % (coverart_url, "/tmp/"), shell=True )
					self.logger.debug("Spotify coverart downloaded")
					coverart=pygame.image.load("/tmp/" + "cover.png")
					self.logger.debug("Spotify coverart loaded")
					self.image["cover"] = pygame.transform.scale(coverart, (228, 228))
					self.logger.debug("Spotify coverart placed")
					self.processingCover = False
					self.coverFetched = True
					self.cover = True
			except Exception, e:
				self.logger.exception(e)
				pass

		# No existing coverart, try to fetch from LastFM
		if not self.cover and self.lastfm_connected:

			try:
				lastfm_album = self.lfm.get_album(self.artist, self.album)
				self.logger.debug("caT album: %s" % lastfm_album)
			except Exception, e:
				# TODO: Check connection - now it is assumed that there is none
				self.lastfm_connected = False
				self.logger.exception(e)
				raise

			if lastfm_album:
				try:
					coverart_url = lastfm_album.get_cover_image(2)
					self.logger.debug("caT curl: %s" % coverart_url)
					if coverart_url:
						self.logger.debug("caT sp start")
						subprocess.check_output("wget -q %s -O %s/cover.png" % (coverart_url, "/tmp/"), shell=True )
						self.logger.debug("caT sp end")
						coverart=pygame.image.load("/tmp/" + "cover.png")
						self.logger.debug("caT c loaded")
						self.image["cover"] = pygame.transform.scale(coverart, (228, 228))
						self.logger.debug("caT c placed")
						self.processingCover = False
						self.coverFetched = True
						self.cover = True
				except Exception, e:
					self.logger.exception(e)
					pass
					
		# Processing finished
		self.processingCover = False
		self.logger.debug("caT end")

	def resetUpdates(self):
		self.updateTrackInfo = False
		self.updateAlbum	 = False
		self.updateElapsed	 = False
		self.updateRandom	 = False
		self.updateRepeat	 = False
		self.updateVolume	 = False
		self.updateState	 = False
		self.updateAll		 = False
		
	def update_all(self):
		self.updateAll = True
		
	def toggle_backlight(self):
		bl = (self.backlight + 1) % 2
		if bl == 1:
			self.turn_backlight_on()
		else:
			self.turn_backlight_off()

	def turn_backlight_off(self):
		self.logger.debug("Backlight off")
		subprocess.call("echo '0' > /sys/class/gpio/gpio508/value", shell=True)
		self.backlight = 0

	def turn_backlight_on(self):
		self.logger.debug("Backlight on")
		subprocess.call("echo '1' > /sys/class/gpio/gpio508/value", shell=True)
		self.backlight = 1

		# Update screen timeout timer
		if config.screen_timeout > 0:
			self.update_screen_timeout()
		
	def get_backlight_status(self):
		return self.backlight

	def get_playlist_status(self):
		return self.showPlaylist

	def get_playlists_status(self):
		return self.showPlaylists

	def toggle_playlists(self, state="Toggle"):
		self.playlists = self.pc.get_playlists()

		# Remove Radio from playlists
		for i in reversed(range(len(self.playlists))):
			if "playlist" in self.playlists[i]:
				if self.playlists[i].get('playlist') == config.radio_playlist:
					self.playlists.pop(i)

		if state == "Toggle":
			self.showPlaylists = not self.showPlaylists
		elif state == "True":
			self.showPlaylists = True
		elif state == "False":
			self.showPlaylists = False

		# Clear scroll offset
		self.offset = 0

		# Ensure that both are not active at the same time
		if self.showPlaylists:
			self.showPlaylist = False
		self.updateAll = True

	def toggle_playlist(self, state="Toggle"):
		self.playlist = self.pc.get_playlist()
		if state == "Toggle":
			self.showPlaylist = not self.showPlaylist
		elif state == "True":
			self.showPlaylist = True
		elif state == "False":
			self.showPlaylist = False

		# Ensure that both are not active at the same time
		if self.showPlaylist:
			self.showPlaylists = False
		self.updateAll = True

	def item_selector(self, number):
		if self.showPlaylist and not self.showPlaylists:
			if number + self.offset < len(self.playlist): 
				self.pc.play_item(number + self.offset)
			self.showPlaylist = False
			self.updateAll = True
		elif self.showPlaylists and not self.showPlaylist:
			if number + self.offset < len(self.playlists):
				self.pc.load_playlist(self.playlists[number + self.offset]["playlist"])
				self.pc.control_player("play", "mpd")
			self.showPlaylists = False
			#self.pc.control_player("mpd")
			self.updateAll = True

		# Clear offset
		self.offset = 0
		
	def inc_offset(self, number):
		self.offset = self.offset - number
		
		# Limits for offset
		if self.offset < 0:
			self.offset = 0
		# Disable scroll if all items fit on the screen
		if (self.showPlaylists) and len(self.playlists) <= 8:
			self.offset = 0
		# Don't overscroll
		elif (self.showPlaylists) and len(self.playlists) - 8 < self.offset:
			self.offset = len(self.playlists) - 8
		
		# Disable scroll if all items fit on the screen
		if (self.showPlaylist) and len(self.playlist) <= 8:
			self.offset = 0
		# Don't overscroll
		elif (self.showPlaylist) and len(self.playlist) - 8 < self.offset:
			self.offset = len(self.playlist) - 8
		self.logger.debug("Offset: %s" % self.offset)

	def update_screen_timeout(self):
		self.screen_timeout_time = datetime.datetime.now() + timedelta(seconds=config.screen_timeout)		
