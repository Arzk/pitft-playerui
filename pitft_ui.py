# -*- coding: utf-8 -*-
import sys, pygame
from pygame.locals import *
import time
import subprocess
import os
import glob
import re
import CDDB
import DiscID
import httplib
import config
from math import ceil
from threading import Thread
from mpd import MPDClient
import datetime
from datetime import timedelta

class PitftPlayerui:
	def __init__(self, client, lfm, logger):

		self.mpdc = client
		self.lfm = lfm
		self.logger = logger

		# Paths
		self.path = os.path.dirname(sys.argv[0]) + "/"
		os.chdir(self.path)
		
		# Fonts
		self.fontfile = self.path + "helvetica-neue-bold.ttf"
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
		# Threads
		self.coverartThread = None
		self.oldCoverartThreadRunning = False

		# Things to remember
		self.screen_timeout_time = 0
		self.processingCover = False
		self.coverFetched = False
		self.mpd_status = {}
		self.mpd_song = {}
		self.spotify_status = {}
		self.spotify_song = {}
		self.playlist = {}
		self.playlists = {}
		self.reconnect = False

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
		
		self.i = 0

		# CDDA variables
		self.disc_id = {}
		self.artist_album = {}
 		self.cdda_query_status = {}
		self.cdda_query_info = {}
		self.cdda_read_status = {}
		self.cdda_read_info = {}

		# What to update
		self.updateTrackInfo = False
		self.updateAlbum	 = False	
		self.updateElapsed	 = False
		self.updateRandom	 = False
		self.updateRepeat	 = False
		self.updateVolume	 = False
		self.updateState	 = False
		self.updateAll		 = True

		# Alternative views
		self.showPlaylist	 = False
		self.showPlaylists	 = False

		# Active player. Determine later
		self.active_player 	= ""

		# Offset for list scrolling
		self.offset 		= 0

		# Print data
		self.logger.info("MPD server version: %s" % self.mpdc.mpd_version)
		
		# Turn backlight on
		self.turn_backlight_on()

	def determine_active_player(self, old_spotify_status, old_mpd_status):

		# Determine active player if not set
		try:
			if not self.active_player:

				# Spotify playing, MPD not
				if self.spotify_status["state"] == "play" and not self.mpd_status["state"] == "play":
					self.switch_active_player("spotify")

				# MPD playing, Spotify not
				elif not self.spotify_status["state"] == "play" and self.mpd_status["state"] == "play":
					self.switch_active_player("mpd")

				# Neither playing - default to mpd
				elif not self.spotify_status["state"] == "play" and not self.mpd_status["state"] == "play":
					self.switch_active_player("mpd")

				# Both playing - default to mpd and pause Spotify
				else:
					self.switch_active_player("mpd")
					self.control_player("pause", "spotify")
		
			# Started playback - switch and pause other player
			# Spotify started playing - switch
			if self.spotify_status["state"] == "play" and not old_spotify_status == "play" and old_spotify_status:
				self.switch_active_player("spotify")
				if self.mpd_status["state"] == "play":
					self.control_player("pause", "mpd")
				# Turn display on 
				if config.screen_timeout > 0 and not self.get_backlight_status():
					self.turn_backlight_on()
				self.logger.debug("Spotify started, pausing mpd")

			# MPD started playing - switch
			if self.mpd_status["state"] == "play" and not old_mpd_status == "play" and old_mpd_status:
				self.switch_active_player("mpd")
				if self.spotify_status["state"] == "play":
					self.control_player("pause", "spotify")
				# Turn display on 
				if config.screen_timeout > 0 and not self.get_backlight_status():
					self.turn_backlight_on()
				self.logger.debug("mpd started, pausing Spotify")
		except:
				self.switch_active_player("")
				self.logger.debug("Can't determine active player yet")

	def refresh_players(self):
		
		# Save old status
		try:
			old_spotify_status = self.spotify_status["state"]
			old_mpd_status = self.mpd_status["state"]
		except:
			old_spotify_status = ""
			old_mpd_status = ""

		# Refresh players
		if config.mpd_host:
			self.refresh_mpd()

		if config.spotify_host:
			self.refresh_spotify()

		# Get active player	
		self.determine_active_player(old_spotify_status, old_mpd_status)

		# Use active player's information
		if self.active_player == "spotify":
			self.status = self.spotify_status
			self.song = self.spotify_song
			
		elif self.active_player == "mpd":
			self.status = self.mpd_status
			self.song = self.mpd_song
		else:
			self.status = {}
			self.song = {}

	def refresh_spotify(self):
		try:
			status = self.spotify_control("info","status")
			#self.logger.debug(status)
			metadata = self.spotify_control("info","metadata")
		except: 
			status = {}
			metadata = {}

		self.spotify_status["active"] = False
		# Extract state from strings
		if status:
			for line in status.split("\n"):
				# Active device in Spotify
				if "active" in line:
					if "true" in line:
						self.spotify_status["active"] = True
					else:
						self.spotify_status["active"] = False
				if "playing" in line:
					if "true" in line and self.spotify_status["active"]:
						self.spotify_status["state"] = "play"
					else:
						self.spotify_status["state"] = "pause"
				if "shuffle" in line:
					if "true" in line and self.spotify_status["active"]:
						self.spotify_status["random"] = 1
					else:
						self.spotify_status["random"] = 0
				if "repeat" in line:
					if "true" in line and self.spotify_status["active"]:
						self.spotify_status["repeat"] = 1
					else:
						self.spotify_status["repeat"] = 0

		if metadata and self.spotify_status["active"]:
			# Parse multiline string of type
			# '  "album_name": "Album", '
			# Split lines and remove leading '"' + ending '", '
			for line in metadata.split("\n"):
				if "album_name" in line:
					self.spotify_song["album"] = line.split(": ")[1][1:-3].decode('utf-8')
				if "artist_name" in line:
					self.spotify_song["artist"] = line.split(": ")[1][1:-3].decode('utf-8')
				if "track_name" in line:
					self.spotify_song["title"] = line.split(": ")[1][1:-3].decode('utf-8')
				if "cover_uri" in line:
					self.spotify_song["cover_uri"] = line.split(": ")[1][1:-3].decode('utf-8')
		else:
			self.spotify_song = {}
			
	def refresh_mpd(self):
		if self.reconnect:
			self.reconnect_mpd()
		if self.reconnect == False:
			connection = False
			try:
				self.mpd_status = self.mpdc.status()
				self.mpd_song = self.mpdc.currentsong()
				connection = True

				# Read CDDB if playing CD
				if "file" in self.mpd_song and config.cdda_enabled:
					if "cdda://" in self.mpd_song["file"].decode('utf-8'):
						self.query_cddb()
					

			except Exception as e:
				self.logger.debug(e)
				connection = False
				self.mpd_status = {}
				self.mpd_song = {}

			if connection == False:
				try:
					if e.errno == 32:
						self.reconnect = True
					else:
						print "Nothing to do"
				except Exception, e:
					self.reconnect = True
					self.logger.debug(e)

	def reconnect_mpd(self):
		self.logger.info("Reconnecting to MPD server")
		client = MPDClient()
		client.timeout = 10
		client.idletimeout = None
		noConnection = True
		while noConnection:
			try:
				client.connect("config.mpd_host", config.mpd_port)
				noConnection=False
			except Exception, e:
				self.logger.info(e)
				noConnection=True
				time.sleep(15)
		self.mpdc = client
		self.reconnect = False
		self.logger.info("Connection to MPD server established.")

	def query_cddb(self):
		# File has changed?
		try:
			file = self.mpd_song["file"].decode('utf-8')
		except:
			file = "";

		if self.file != file:
			self.file = file
			try:
				cdrom = DiscID.open()
				disc_id = DiscID.disc_id(cdrom)
			except:
				cdrom = ""
				disc_id = {}

			# Disc has changed - query again
			if self.disc_id != disc_id:
				self.disc_id = disc_id
				self.logger.debug("Disc ID: %s" % disc_id)
				try:
					(self.cdda_query_status, self.cdda_query_info) = CDDB.query(disc_id)
				except:
					self.cdda_query_status = {}
					self.cdda_query_info = {}
				self.logger.debug("CDDB Query status: %s" % self.cdda_query_status)
						
				# Exact match found
				try:
					if self.cdda_query_status == 200:
						(self.cdda_read_status, self.cdda_read_info) = CDDB.read(self.cdda_query_info["category"], self.cdda_query_info["disc_id"])
						self.logger.debug("CDDB Read Status: %s" % self.cdda_read_status)
					# Multiple matches found - pick first
					elif self.cdda_query_status == 210 or self.cdda_query_status == 211:
						(self.cdda_read_status, self.cdda_read_info) = CDDB.read(self.cdda_query_info[0]["category"], self.cdda_query_info[0]["disc_id"])
						self.logger.debug("CDDB Read Status: %s" % self.cdda_read_status)
					# No match found
					else:
						self.logger.info("CD query failed, status: %s " % self.cdda_query_status)
				except:
					self.cdda_read_status = 0
					self.cdda_read_info = {}
					
				# Read successful - Save data
				if self.cdda_read_status == 210:
					try:
						self.artist_album = self.cdda_read_info["DTITLE"].split(" / ")
					except:
						self.artist_album = {};
				else:
					self.logger.info("CDDB read failed, status: %s" % self.cdda_read_status)

		# Fill song information from CD

		# Artist
		try:
			self.mpd_song["artist"] = self.artist_album[0]
		except:
			self.mpd_song["artist"] = ""
		# Album
		try:
			self.mpd_song["album"] = self.artist_album[1]
		except:
			self.mpd_song["album"] = ""
		# Date
		try:
			self.mpd_song["date"] = self.cdda_read_info["DYEAR"].decode('utf-8')
		except:
			self.mpd_song["date"] = ""
		# Track Number
		try:
			self.mpd_song["track"] = file.split("cdda:///")[-1].split()[0]
		except:
			self.mpd_song["track"] = file.split("cdda:///")[-1].split()[0]
		# Title
		try:
			number=int(self.mpd_song["track"]) - 1
			self.mpd_song["title"] = self.cdda_read_info["TTITLE" + str(number)].decode('utf-8')
		except:
			self.mpd_song["title"] = ""
		# Time
		try:
			if int(self.mpd_song["track"]) == int(self.disc_id[1]):
				# The final track has to be count with 
				# CD length in seconds - start frame of final track
				# 75 frames = 1 second
				self.mpd_song["time"] = self.disc_id[int(self.mpd_song["track"]) + 2] - self.disc_id[int(self.mpd_song["track"]) + 1] / 75
			else:
				# For other tracks count from start frame of track and next track.
				self.mpd_song["time"] = (self.disc_id[int(self.mpd_song["track"]) + 2] - self.disc_id[int(self.mpd_song["track"]) + 1]) / 75
		except:
			self.mpd_song["time"] = 0

	def parse_song(self):
		# -------------
		# |  PARSE    |
		# -------------
		
		# Artist
		try:
			artist = self.song["artist"].decode('utf-8')
		except:
			artist = ""

		# Album
		try:
			album = self.song["album"].decode('utf-8')
		except:
			album = ""
		# Album Date
		try:
			date = self.song["date"].decode('utf-8')
		except:
			date = ""
		# Track Number
		try:
			track = self.song["track"].decode('utf-8')
		except:
			track = ""
		# Track Title
		try:
			if self.song["title"]:
				title = self.song["title"].decode('utf-8')
			else:
				title = self.song["file"].decode('utf-8')
		except:
			title = ""
	
		# Time elapsed
		try:
			min = int(ceil(float(self.status["elapsed"])))/60
			min = min if min > 9 else "0%s" % min
			sec = int(ceil(float(self.status["elapsed"])%60))
			sec = sec if sec > 9 else "0%s" % sec
			timeElapsed = "%s:%s" % (min,sec)
		except:
			timeElapsed = "00:00"

		# Time total
		try:
			min = int(ceil(float(self.song["time"])))/60
			sec = int(ceil(float(self.song["time"])%60))
			min = min if min > 9 else "0%s" % min
			sec = sec if sec > 9 else "0%s" % sec
			timeTotal = "%s:%s" % (min,sec)
		except:
			timeTotal = "00:00"

		# Time elapsed percentage
		try:
			timeElapsedPercentage = float(self.status["elapsed"])/float(self.song["time"])
		except:
			timeElapsedPercentage = 0

		# Playback status
		try:
			playbackStatus = self.status["state"]
		except:
			playbackStatus = "stop"

		# Repeat
		try:
			repeat = int(self.status["repeat"])
		except:
			repeat = 0

		# Random
		try:
			random = int(self.status["random"])
		except:
			random = 0

		# Volume
		try:
			volume = int(self.status["volume"])
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
			if self.active_player == "spotify" and config.mpd_host:
				surface.blit(self.image["button_spotify"], (418, 8))
			elif self.active_player == "mpd" and config.spotify_host:
				surface.blit(self.image["button_mpd"], (418, 8))
					
			if config.mpd_host:
				surface.blit(self.image["button_playlists"], (418, 66))
			
			if config.cdda_enabled:
				surface.blit(self.image["button_cd"], (418, 124))
			
			if config.radio_playlist:
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
			if self.active_player == "mpd":
				text = self.font["elapsed"].render(self.timeTotal, 1,(230,228,227))
				surface.blit(text, (429, 238)) # Track length

		# Spotify-connect-web api doesn't deliver elapsed information
		if self.updateElapsed and self.active_player == "mpd":
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
		if config.screen_timeout > 0:
			if self.status["state"] == "play": 
				self.updateScreenTimeout()
			# Nothing playing for 5 seconds, turn off screen if not already off
			elif self.screen_timeout_time < datetime.datetime.now() and self.backlight:
				self.turn_backlight_off()

		# Reset updates
		self.resetUpdates()

	def resetUpdates(self):
		self.updateTrackInfo = False
		self.updateAlbum	 = False
		self.updateElapsed	 = False
		self.updateRandom	 = False
		self.updateRepeat	 = False
		self.updateVolume	 = False
		self.updateState	 = False
		self.updateAll		 = False
		
	def fetch_coverart(self):
		self.logger.debug("caT start")
		self.processingCover = True
		self.coverFetched = False
		self.cover = False

		# Search for local coverart
		if "file" in self.song and self.active_player == "mpd" and config.library_path:
		
			folder = os.path.dirname(config.library_path + "/" + self.song["file"])
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
		elif "cover_uri" in self.song and self.active_player == "spotify" and config.spotify_host:
			try:
				coverart_url = config.spotify_host + ":" + config.spotify_port + "/api/info/image_url/" + self.song["cover_uri"]
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
			except:
				self.logger.exception(e)
				pass

		# No existing coverart, try to fetch from LastFM
		if not self.cover:

			try:
				lastfm_album = self.lfm.get_album(self.artist, self.album)
				self.logger.debug("caT album: %s" % lastfm_album)
			except Exception, e:
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

	def toggle_random(self):
		if self.active_player == "spotify":
			self.spotify_control("playback","shuffle")
		else:
			random = (self.random + 1) % 2
			self.mpdc.random(random)

	def toggle_repeat(self):
		if self.active_player == "spotify":
			self.spotify_control("playback","repeat")
		else:
			repeat = (self.repeat + 1) % 2
			self.mpdc.repeat(repeat)

	# Direction: +, -
	def set_volume(self, amount, direction=""):
		if direction == "+":
			volume = self.volume + amount
		elif direction == "-":
			volume = self.volume - amount
		else:
			volume = amount

		volume = 100 if volume > 100 else volume
		volume = 0 if volume < 0 else volume
		self.mpdc.setvol(volume)	
			
	def toggle_playback(self):
			status = self.playbackStatus
			if status == "play":
				if self.active_player == "spotify":
					self.spotify_control("playback","pause")
				else:
					self.mpdc.pause()
			else:
				if self.active_player == "spotify":
					self.spotify_control("playback","play")
				else:
					self.mpdc.play()
	
	def control_player(self, command, player="active"):
		if command == "repeat":
			self.toggle_repeat()
		elif command == "random":
			self.toggle_random()
		elif command == "cd":
			self.play_cd()
		elif command == "radio":
			self.load_playlist(config.radio_playlist)
			self.mpdc.play()
		elif command == "mpd":
			self.switch_active_player("mpd")
		elif command == "spotify":
			self.switch_active_player("spotify")

		elif (player == "active" and self.active_player == "spotify") or player == "spotify":
			# Translate commands
			if command == "stop":
				command = "pause"
			if command == "previous":
				command = "prev"
			# Prevent commands not implemented in api
			if command != "ff" or command != "rwd": 
				self.spotify_control("playback", command)
		elif (player == "active" and self.active_player == "mpd") or player == "mpd":
			if command == "next":
				self.mpdc.next()
			elif command == "previous":
				self.mpdc.previous()
			elif command == "pause":
				self.mpdc.pause()
			elif command == "play":
				self.mpdc.play()
			elif command == "stop":
				self.mpdc.stop()
			elif command == "rwd":
				self.mpdc.seekcur("-10")
			elif command == "ff":
				self.mpdc.seekcur("+10")
			else:
				pass
		else:
			self.logger.debug("No player specified for control")

	def load_playlist(self, command):
		self.mpdc.clear()
		self.mpdc.load(command)

	def toggle_backlight(self):
		bl = (self.backlight + 1) % 2
		if bl == 1:
			self.turn_backlight_on()
		else:
			self.turn_backlight_off()

	def turn_backlight_off(self):
		self.logger.debug("Backlight off")
#		subprocess.call("/home/pi/bin/display off", shell=True)
		subprocess.call("echo '0' > /sys/class/gpio/gpio508/value", shell=True)
		self.backlight = 0

	def turn_backlight_on(self):
		self.logger.debug("Backlight on")
#		subprocess.call("/home/pi/bin/display on", shell=True)
		subprocess.call("echo '1' > /sys/class/gpio/gpio508/value", shell=True)
		self.backlight = 1

		# Update screen timeout timer
		if config.screen_timeout > 0:
			self.updateScreenTimeout()
		
	def get_backlight_status(self):
		return self.backlight

	def get_playlist_status(self):
		return self.showPlaylist

	def get_playlists_status(self):
		return self.showPlaylists

	def toggle_playlists(self, state="Toggle"):
		self.playlists = self.mpdc.listplaylists()

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
		self.playlist = self.mpdc.playlistinfo()
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

	def update_all(self):
		self.updateAll = True

	def item_selector(self, number):
		if self.showPlaylist and not self.showPlaylists:
			if number + self.offset < len(self.playlist): 
				self.mpdc.play(number + self.offset)
			self.showPlaylist = False
			self.updateAll = True
		elif self.showPlaylists and not self.showPlaylist:
			if number + self.offset < len(self.playlists):
				self.mpdc.clear()
				self.mpdc.load(self.playlists[number + self.offset]["playlist"])
				self.mpdc.play()
			self.showPlaylists = False
			self.switch_active_player("mpd")
			self.updateAll = True

		# Clear offset
		self.offset = 0
		
	def play_cd(self):
		self.logger.info("Playing CD")
		try:
			cdrom = DiscID.open()
			disc_id = DiscID.disc_id(cdrom)
		except:
			disc_id = ""
		if disc_id:
			self.mpdc.clear()
			number_of_tracks = int(disc_id[1])
			for i in range (1, number_of_tracks):
				self.mpdc.add("cdda:///" + str(i))

			# Pause Spotify
			self.switch_active_player("mpd")
			self.updateAll = True

			self.mpdc.random(0)
			self.mpdc.repeat(0)
			self.mpdc.play()

	# Using api from spotify-connect-web
	# Valid methods:  playback, info
	# Valid info commands: metadata, status, image_url/<image_url>, display_name
	# Valid playback commands: play, pause, prev, next, shuffle, repeat, volume
	def spotify_control(self, method, command):
		#c = httplib.HTTPConnection('localhost', 4000)
		c = httplib.HTTPConnection(config.spotify_host, config.spotify_port)
		c.request('GET', '/api/'+method+'/'+command, '{}')
		doc = c.getresponse().read()
		return doc

	def switch_active_player(self, state="toggle"):
		if state == "toggle":
			if self.active_player == "spotify":
				self.active_player = "mpd"
			else:
				self.active_player = "spotify"
		else:
			self.active_player = state

		# Update screen
		self.updateAll = True

	def get_active_player(self):
		return self.active_player

	def inc_offset(self, number):
		self.offset = self.offset - number
		
		# Limits for offset
		if self.offset < 0:
			self.offset = 0
		if (self.showPlaylists) and len(self.playlists) <= 8:
			self.offset = 0
		elif (self.showPlaylists) and len(self.playlists) - 8 < self.offset:
			self.offset = len(self.playlists) - 8
		
		if (self.showPlaylist) and len(self.playlist) <= 8:
			self.offset = 0
		elif (self.showPlaylist) and len(self.playlist) - 8 < self.offset:
			self.offset = len(self.playlist) - 8
		self.logger.debug("Offset: %s" % self.offset)

	def updateScreenTimeout(self):
		self.screen_timeout_time = datetime.datetime.now() + timedelta(seconds=config.screen_timeout)		