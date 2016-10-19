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
		self.lfm_connected = False
		
		# Paths
		self.path = os.path.dirname(sys.argv[0]) + "/"
		os.chdir(self.path)

		# Threads
		self.coverartThread = None
		self.oldCoverartThreadRunning = False
	
		# Fonts
		self.fontfile = self.path + config.fontfile
		self.font = {}
		self.font['details']     = pygame.font.Font(self.fontfile, 16)
		self.font['elapsed']     = pygame.font.Font(self.fontfile, 16)
		self.font['playlist']    = pygame.font.Font(self.fontfile, 20)
		self.font['field']       = pygame.font.Font(self.fontfile, 20)
		self.color = {}
		self.color['font']       = 230,228,227
		self.color['highlight']  = 230,228,0
		
		# Images
		self.image = {}
		self.image["background"]           = pygame.image.load(self.path + "pics/" + "background.png")
		self.image["coverart_place"]       = pygame.image.load(self.path + "pics/" + "coverart-placer.png")
		self.image["coverart_border"]      = pygame.image.load(self.path + "pics/" + "coverart-border.png")
		self.image["details"]              = pygame.image.load(self.path + "pics/" + "details.png")
		self.image["field"]                = pygame.image.load(self.path + "pics/" + "field-value.png")
		self.image["progress_bg"]          = pygame.image.load(self.path + "pics/" + "position-background.png")
		self.image["progress_fg"]          = pygame.image.load(self.path + "pics/" + "position-foreground.png")
		self.image["icon_randomandrepeat"] = pygame.image.load(self.path + "pics/" + "randomandrepeat.png")
		self.image["icon_screenoff"]       = pygame.image.load(self.path + "pics/" + "screen-off.png")
		
		## Buttons                           
		self.image["button_next"]          = pygame.image.load(self.path + "pics/" + "button-next.png")
		self.image["button_pause"]         = pygame.image.load(self.path + "pics/" + "button-pause.png")
		self.image["button_play"]          = pygame.image.load(self.path + "pics/" + "button-play.png")
		self.image["button_prev"]          = pygame.image.load(self.path + "pics/" + "button-prev.png")
		self.image["button_volumeminus"]   = pygame.image.load(self.path + "pics/" + "button-volumeminus.png")
		self.image["button_volumeplus"]    = pygame.image.load(self.path + "pics/" + "button-volumeplus.png")
		self.image["button_toggle_off"]    = pygame.image.load(self.path + "pics/" + "toggle-off.png")
		self.image["button_toggle_on"]     = pygame.image.load(self.path + "pics/" + "toggle-on.png")
		self.image["button_spotify"]       = pygame.image.load(self.path + "pics/" + "button-spotify.png")
		self.image["button_mpd"]           = pygame.image.load(self.path + "pics/" + "button-mpd.png")
		self.image["button_radio"]         = pygame.image.load(self.path + "pics/" + "button-radio.png")
		self.image["button_cd"]            = pygame.image.load(self.path + "pics/" + "button-cd.png")
		self.image["button_playlists"]     = pygame.image.load(self.path + "pics/" + "button-playlists.png")
		
		# Sizes
		self.size = {}
		if config.resolution[0] == 480 and config.resolution[1] == 320:
			self.size['margin']             = 4
			self.size['padding_x']          = 8
			self.size['padding_y']          = 4
			self.size['coverart']           = 228
			self.size['selectorbutton']     = 58
			self.size['controlbutton']      = 48
			self.size['button_screenoff']   = 60
			self.size['icon_screenoff']     = 20, 16
			self.size['togglebutton']       = 62, 25
			self.size['volume_text_width']  = 46
			self.size['volume_field']       = 44, 24
			self.size['volume_fieldoffset'] = 6
			self.size['trackinfo_height']   = 20 # Row height
			self.size['details']            = 46,52
			self.size['elapsed']            = 40
			self.size['elapsedmargin']      = 6
			self.size['elapsedoffset']      = 7
			self.size['controlbuttonsoffset']      = 16
			self.size['progressbar']        = 370, 8
			self.size['progressbar_height'] = 20
			self.size['listitem_height']     = 30
		elif config.resolution[0] == 320 and config.resolution[1] == 240:
			self.size['margin']             = 4
			self.size['padding_x']          = 4
			self.size['padding_y']          = 2
			self.size['coverart']           = 158
			self.size['selectorbutton']     = 42
			self.size['controlbutton']      = 38
			self.size['button_screenoff']   = 40
			self.size['icon_screenoff']     = 20, 16
			self.size['togglebutton']       = 62, 25
			self.size['volume_text_width']  = 40
			self.size['volume_field']       = 34, 26
			self.size['volume_fieldoffset'] = 4
			self.size['trackinfo_height']   = 16 # Row height
			self.size['details']            = 36,42
			self.size['elapsed']            = 32
			self.size['elapsedmargin']      = 6
			self.size['elapsedoffset']      = 4
			self.size['controlbuttonsoffset'] = 7
			self.size['progressbar']        = config.resolution[0] - 2 * (self.size['elapsed'] + self.size['elapsedmargin'] + self.size['margin'] + 5), 8    #205, 8
			self.size['progressbar_height'] = 20
			self.size['listitem_height']     = 20

			# Resize fonts
			self.font['details']     = pygame.font.Font(self.fontfile, 14)
			self.font['elapsed']     = pygame.font.Font(self.fontfile, 14)
			self.font['playlist']    = pygame.font.Font(self.fontfile, 14)
			self.font['field']       = pygame.font.Font(self.fontfile, 16)
			
			# Scale images
			try:
				self.image['background']         = pygame.transform.scale(self.image['background'], (config.resolution))
				self.image['coverart_place']     = pygame.transform.scale(self.image['coverart_place'], (self.size['coverart'], self.size['coverart']))
				self.image['coverart_border']    = pygame.transform.scale(self.image['coverart_border'], (self.size['coverart'], self.size['coverart']))
				self.image['details']            = pygame.transform.scale(self.image['details'], (self.size['details']))
				self.image['field']              = pygame.transform.scale(self.image['field'], (self.size['volume_field'][0] + 2, self.size['volume_field'][1] + 2))
				self.image['progress_bg']        = pygame.transform.scale(self.image['progress_bg'], (self.size['progressbar']))
				self.image['progress_fg']        = pygame.transform.scale(self.image['progress_fg'], (self.size['progressbar']))
				self.image['button_next']        = pygame.transform.scale(self.image['button_next'], (self.size['controlbutton'],self.size['controlbutton']))
				self.image['button_pause']       = pygame.transform.scale(self.image['button_pause'], (self.size['controlbutton'],self.size['controlbutton']))
				self.image['button_play']        = pygame.transform.scale(self.image['button_play'], (self.size['controlbutton'],self.size['controlbutton']))
				self.image['button_prev']        = pygame.transform.scale(self.image['button_prev'], (self.size['controlbutton'],self.size['controlbutton']))
				self.image['button_volumeminus'] = pygame.transform.scale(self.image['button_volumeminus'], (self.size['controlbutton'],self.size['controlbutton']))
				self.image['button_volumeplus']  = pygame.transform.scale(self.image['button_volumeplus'], (self.size['controlbutton'],self.size['controlbutton']))
				self.image['button_spotify']     = pygame.transform.scale(self.image['button_spotify'], (self.size['selectorbutton'],self.size['selectorbutton']))
				self.image['button_mpd']         = pygame.transform.scale(self.image['button_mpd'], (self.size['selectorbutton'],self.size['selectorbutton']))
				self.image['button_radio']       = pygame.transform.scale(self.image['button_radio'], (self.size['selectorbutton'],self.size['selectorbutton']))
				self.image['button_cd']          = pygame.transform.scale(self.image['button_cd'], (self.size['selectorbutton'],self.size['selectorbutton']))
				self.image['button_playlists']   = pygame.transform.scale(self.image['button_playlists'], (self.size['selectorbutton'],self.size['selectorbutton']))
			except Exception, e:
				self.logger.debug(e)

		else:
			# TODO: Not a nice shutdown, but crashes like it should
			self.logger.info("Unsupported resolution: %s" % config.resolution)
	
		# Positioning
		self.pos = {}
		
		# Screen borders
		self.pos['left']         = self.size['margin'] #4
		self.pos['right']        = config.resolution[0] - self.size['margin'] #476
		self.pos['top']          = self.size['margin'] #4
		self.pos['bottom']       = config.resolution[1] - self.size['margin'] #316	
		self.pos['paddedleft']   = self.pos['left'] + self.size['padding_x'] #12
		self.pos['paddedright']  = self.pos['right'] - self.size['padding_x'] #468
		self.pos['paddedtop']    = self.pos['top'] + self.size['padding_y'] #12
		self.pos['paddedbottom'] = self.pos['bottom'] - self.size['padding_y'] #308

		# Cover art position
		self.pos['coverart']      = self.pos['left'], self.pos['top'] #4

		# Area for track info
		self.pos['bottomdivider'] = self.pos['bottom'] - 78
		
		# Track information 
		self.pos['track']              = self.pos['left'] + self.size['elapsed'] + 16, self.pos['bottom'] - self.size['trackinfo_height']
		self.pos['album']              = self.pos['track'][0], self.pos['track'][1] - self.size['trackinfo_height']
		self.pos['artist']             = self.pos['album'][0], self.pos['album'][1] - self.size['trackinfo_height']
		self.pos['details']            = self.pos['left'] + 2, self.pos['artist'][1] + 4 # 263
		self.pos['progressbar']        = self.pos['left'] + self.size['elapsed'] + 11, self.pos['artist'][1] - 13 # 245
		self.pos['elapsed']            = self.pos['left'] + self.size['elapsedmargin'], self.pos['progressbar'][1] - self.size['elapsedoffset']
		self.pos['track_length']       = self.pos['right'] - self.size['elapsed'] - self.size['elapsedmargin'], self.pos['progressbar'][1] - self.size['elapsedoffset']
		
		# Background refresh for track info
		self.pos['trackinfobackground'] = 0, self.pos['progressbar'][1] - 6
		self.size['trackinfobackground'] = config.resolution[0], config.resolution[1] - self.pos['progressbar'][1] + 6

		# Background refresh for elapsed information
		self.pos['progressbackground'] = 0, self.pos['progressbar'][1] - 6
		self.size['progressbackground'] = self.pos['track_length'][0], self.size['progressbar_height'] #427,20
		
		# Topmost selector button
		self.pos['selectorbutton'] = self.pos['right'] - self.size['selectorbutton'], self.pos['paddedtop'] #418, 8
		
		# Center (pause) control button
		self.pos['controlbutton'] = (self.pos['selectorbutton'][0] + self.size['padding_x'] + self.size['coverart'] - self.size['controlbutton'])/2, \
									self.pos['progressbar'][1] - 2 * self.size['controlbutton'] - self.size['controlbuttonsoffset']	#306, 132
		
		# Selector buttons
		selector_buttons_shown = 0
		self.pos['button_spotify']   = self.pos['selectorbutton'] #418, 8		
		if config.mpd_host and config.mpd_port and config.spotify_host and config.spotify_port:
			selector_buttons_shown = selector_buttons_shown + 1				
		self.pos['button_playlists'] = self.pos['selectorbutton'][0], self.pos['top'] + selector_buttons_shown * self.size['selectorbutton'] #418, 64
		if config.mpd_host and config.mpd_port:
			selector_buttons_shown = selector_buttons_shown + 1
		self.pos['button_cd']        = self.pos['selectorbutton'][0], self.pos['top'] + selector_buttons_shown * self.size['selectorbutton'] #418, 132
		if config.mpd_host and config.mpd_port and config.cdda_enabled:
			selector_buttons_shown = selector_buttons_shown + 1
		self.pos['button_radio']     = self.pos['selectorbutton'][0], self.pos['top'] + selector_buttons_shown * self.size['selectorbutton'] #418, 190
		
		# Control buttons
		self.pos['button_prev']          = self.pos['controlbutton'][0] - self.size['controlbutton'], self.pos['controlbutton'][1] # 258, 132
		self.pos['button_play']          = self.pos['controlbutton'][0]                             , self.pos['controlbutton'][1] # 306, 132
		self.pos['button_next']          = self.pos['controlbutton'][0] + self.size['controlbutton'], self.pos['controlbutton'][1] # 354, 132
		self.pos['button_volumeminus']   = self.pos['controlbutton'][0] - self.size['controlbutton'], self.pos['controlbutton'][1] + self.size['controlbutton'] # 258, 190
		self.pos['button_volumeplus']    = self.pos['controlbutton'][0] + self.size['controlbutton'], self.pos['controlbutton'][1] + self.size['controlbutton'] # 354, 190
		self.pos['volume_field']         = self.pos['controlbutton'][0] - 1                         , self.pos['button_volumeplus'][1] +  self.size['volume_fieldoffset'] # 303, 186
		self.pos['volume_text']          = self.pos['volume_field'][0]                              , self.pos['volume_field'][1] + 3  #304, 189
		self.pos['button_repeat']        = self.pos['controlbutton'][0]                             , self.pos['controlbutton'][1] - self.size['controlbutton'] - self.size['togglebutton'][1] #313,56
		self.pos['button_random']        = self.pos['controlbutton'][0]                             , self.pos['controlbutton'][1] - self.size['controlbutton'] #313,88
		self.pos['icon_randomandrepeat'] = self.pos["button_repeat"][0] - 24                        , self.pos['button_repeat'][1] + 6 #285, 55
		self.pos['icon_screenoff']       = config.resolution[0] - self.size['icon_screenoff'][0]    , config.resolution[1] - self.size['icon_screenoff'][1] # 464, 304
		self.pos['button_screenoff']     = config.resolution[0] - self.size['button_screenoff']     , config.resolution[1] - self.size['button_screenoff'] # 464, 304
		
		# Background refresh for control buttons
		self.pos['repeatbackground']     = self.pos["button_repeat"] # 310,50
		self.size['repeatbackground']    = self.size['togglebutton']
		self.pos['randombackground']     = self.pos["button_random"] # 310,83
		self.size['randombackground']    = self.size['togglebutton']

		self.pos['button_playbackground']  = self.pos['button_play']
		self.size['button_playbackground'] = self.size['controlbutton'], self.size['controlbutton']
				
		# Playlist(s) views
		self.pos['list_left']           = self.pos['left'] #4
		self.pos['list_right']          = self.pos['selectorbutton'][0] - 2 #416
		self.pos['list_top']            = self.pos['top'] #4
		self.pos['list_bottom']         = self.pos['progressbar'][1] - 2 # 243
		self.pos['list_width']          = self.pos['list_right'] - self.pos['list_left'] # 408
		self.pos['list_height']         = self.pos['list_bottom'] - self.pos['list_top'] # 234 -> 239
		
		self.pos['listbackground']      = self.pos['list_left'], self.pos['list_top']
		self.size['listbackground']     = self.pos['list_width'], self.pos['list_height'] #416,234
		

		# Things to remember
		self.screen_timeout_time = 0
		self.processingCover = False
		self.coverFetched    = False
		self.playlist        = {}
		self.playlists       = {}

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
		self.trackfile       = None
		self.artist          = ""
		self.album           = ""
		self.date            = ""
		self.track           = ""
		self.title           = ""
		self.file            = ""
		self.timeElapsed     = "00:00"
		self.timeTotal       = "00:00"
		self.timeElapsedPercentage = 0
		self.playbackStatus  = "stop"
		self.volume          = 0
		self.random          = 0
		self.repeat          = 0
		self.cover           = False

		# Alternative views
		self.showPlaylist	 = False
		self.showPlaylists	 = False

		# Offset for list scrolling
		self.offset          = 0

		# Turn backlight on
		self.backlight_forced_off = False
		self.turn_backlight_on()
		
	def connect_lfm(self):
		self.logger.info("Setting Pylast")
		username = config.username
		password_hash = pylast.md5(config.password_hash)
		self.lfm_connected = False
		try:
			self.lfm = pylast.LastFMNetwork(api_key = config.API_KEY, api_secret = config.API_SECRET)
			self.lfm_connected = True
			self.logger.debug("Connected to Last.fm")
		except:
			self.lfm = ""
			time.sleep(5)
			self.logger.debug("Last.fm not connected")
			
	def refresh(self):	
		# (re)connect to last.fm
		if not self.lfm_connected and config.API_KEY and config.API_SECRET:
			self.connect_lfm()

		# Refresh information from players
		self.pc.refresh_players()

		# Parse new song information
		self.parse_song()
		
		# Something is playing - keep screen on
		if self.pc.status and config.screen_timeout > 0 and not self.backlight_forced_off:
			if self.pc.status["state"] == "play":
				self.update_screen_timeout()
		
			# Nothing playing for n seconds, turn off screen if not already off
			elif self.screen_timeout_time < datetime.datetime.now() and self.backlight:
				self.turn_backlight_off()

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
	
		if self.updateAll:
			self.updateTrackInfo = True
			self.updateAlbum	 = True
			self.updateElapsed	 = True
			self.updateRandom	 = True
			self.updateRepeat	 = True
			self.updateVolume	 = True
			self.updateState	 = True
			
			surface.blit(self.image["background"], (0,0))
			surface.blit(self.image["coverart_place"],(self.pos['coverart']))
			surface.blit(self.image["details"], (self.pos['details']))
			surface.blit(self.image["progress_bg"], (self.pos['progressbar']))
			
			# Control buttons
			surface.blit(self.image["button_prev"], (self.pos["button_prev"]))
			surface.blit(self.image["button_next"], (self.pos["button_next"]))
			surface.blit(self.image["icon_randomandrepeat"], (self.pos["icon_randomandrepeat"]))
			
			if config.volume_enabled and self.pc.get_active_player() == "mpd":
				surface.blit(self.image["button_volumeminus"], (self.pos["button_volumeminus"]))
				surface.blit(self.image["button_volumeplus"], (self.pos["button_volumeplus"]))
				
			surface.blit(self.image["icon_screenoff"], (self.pos["icon_screenoff"]))

			# Change player button, if more than 1 player available
			if self.pc.get_active_player() == "spotify" and self.pc.mpd:
				surface.blit(self.image["button_spotify"], (self.pos["button_spotify"]))
			elif self.pc.get_active_player() == "mpd" and self.pc.spotify:
				surface.blit(self.image["button_mpd"], (self.pos["button_spotify"]))
					
			if self.pc.mpd:
				surface.blit(self.image["button_playlists"], (self.pos["button_playlists"]))
			
			if self.pc.mpd and config.cdda_enabled:
				surface.blit(self.image["button_cd"], (self.pos["button_cd"]))
			
			if self.pc.mpd and config.radio_playlist:
				surface.blit(self.image["button_radio"], (self.pos["button_radio"]))

		if self.updateAlbum or self.coverFetched:
			if self.cover:
				surface.blit(self.image["cover"], (self.pos['coverart']))
				surface.blit(self.image["coverart_border"],(self.pos['coverart']))
				self.coverFetched = False
			else:
				# Reset background
				surface.blit(self.image["coverart_place"],(self.pos['coverart']))
			
		if self.updateTrackInfo:
			if not self.updateAll:
				surface.blit(self.image["background"], (self.pos['trackinfobackground']), (self.pos['trackinfobackground'], self.size['trackinfobackground'])) # reset background
				surface.blit(self.image["details"], (self.pos['details']))
				surface.blit(self.image["progress_bg"], (self.pos['progressbar']))
				surface.blit(self.image["icon_screenoff"], (self.pos["icon_screenoff"]))	# redraw screenoff icon

			text = self.font["details"].render(self.artist, 1,(self.color['font']))
			surface.blit(text, (self.pos['artist'])) # Artist
			if self.date:
				text = self.font["details"].render(self.album + " (" + self.date + ")", 1,(self.color['font']))
			else:
				text = self.font["details"].render(self.album, 1,(self.color['font']))
			surface.blit(text, (self.pos['album'])) # Album
			if self.track:
				text = self.font["details"].render(self.track.zfill(2) + " - " + self.title, 1,(self.color['font']))
			else:
				text = self.font["details"].render(self.title, 1,(self.color['font']))
			surface.blit(text, (self.pos['track'])) # Title
			if self.pc.get_active_player() == "mpd":
				text = self.font["elapsed"].render(self.timeTotal, 1,(self.color['font']))
				surface.blit(text, (self.pos['track_length'])) # Track length

		# Spotify-connect-web api doesn't deliver elapsed information
		if self.updateElapsed and self.pc.get_active_player() == "mpd":
			if not self.updateAll or not self.updateTrackInfo:
				surface.blit(self.image["background"], (self.pos['progressbackground']), (self.pos['progressbackground'], self.size['progressbackground'])) # reset background
				surface.blit(self.image["progress_bg"], (self.pos['progressbar']))
			surface.blit(self.image["progress_fg"], (self.pos['progressbar']),(0,0,int(self.size['progressbar'][0]*self.timeElapsedPercentage),10))
			text = self.font["elapsed"].render(self.timeElapsed, 1,(self.color['font']))
			surface.blit(text, (self.pos['elapsed'])) # Elapsed

		if self.updateRepeat:
			if not self.updateAll:
				surface.blit(self.image["background"], (self.pos['repeatbackground']), (self.pos['repeatbackground'], self.size['repeatbackground'])) # reset background

			if self.repeat == 1:
				surface.blit(self.image["button_toggle_on"], (self.pos["button_repeat"]))
			else:
				surface.blit(self.image["button_toggle_off"], (self.pos["button_repeat"]))

		if self.updateRandom:
			if not self.updateAll:
				surface.blit(self.image["background"], (self.pos['randombackground']), (self.pos['randombackground'], self.size['randombackground'])) # reset background

			if self.random == 1:
				surface.blit(self.image["button_toggle_on"], (self.pos["button_random"]))
			else:
				surface.blit(self.image["button_toggle_off"], (self.pos["button_random"]))

		if self.updateVolume:
			if config.volume_enabled and self.pc.get_active_player() == "mpd":
				if not self.updateAll:
					surface.blit(self.image["field"], (self.pos['volume_field']), ((0,0), self.size['volume_field'])) # Reset field value area
				else:
					surface.blit(self.image["field"], (self.pos['volume_field'])) # Draw field
			
				text = self.font["field"].render(str(self.volume), 1,(self.color['font']))

				pos = self.pos["volume_text"][0] + (self.size["volume_text_width"] - text.get_width())/2
				surface.blit(text, (pos, self.pos["volume_text"][1])) # Volume
				
		if self.updateState:
			if not self.updateAll:
				surface.blit(self.image["background"], (self.pos['button_playbackground']), (self.pos['button_playbackground'], self.size['button_playbackground'])) # reset background
			if self.playbackStatus == "play":
				surface.blit(self.image["button_pause"], (self.pos["button_play"]))
			else:
				surface.blit(self.image["button_play"], (self.pos["button_play"]))

		if self.showPlaylist:
			surface.blit(self.image["background"], (self.pos['listbackground']), (self.pos['listbackground'], self.size['listbackground'])) # reset background
			
			if self.playlist:
				for i in range(0,8):
					try:
						# Parse information
						if "title" in self.playlist[i+self.offset]:
							playlistitem = self.playlist[i+self.offset]["title"]
							if "artist" in self.playlist[i+self.offset]:
								playlistitem = self.playlist[i+self.offset]["artist"] + " - " + playlistitem
							if "pos" in self.playlist[i+self.offset]:
								pos = int(self.playlist[i+self.offset]["pos"]) + 1
								pos = str(pos).rjust(4, ' ')
								playlistitem = pos + ". " + playlistitem

						# No title, get filename
						elif "file" in self.playlist[i+self.offset]:
							playlistitem = self.playlist[i+self.offset]["file"].split("/")[-1]
					except:
						playlistitem = ""

					# Highlight currently playing item
					try:
						if self.playlist[i+self.offset]["pos"] == self.pc.song["pos"]:
							text = self.font["playlist"].render(playlistitem, 1,(self.color['highlight']))
						else: 
							text = self.font["playlist"].render(playlistitem, 1,(self.color['font']))

					except:
						text = self.font["playlist"].render(playlistitem, 1,(self.color['font']))
					surface.blit(text, (self.pos['list_left'],self.pos['list_top'] + self.size['listitem_height']*int(i)),(0,0, self.pos['list_width'],self.size['listitem_height']))

		if self.showPlaylists:
			surface.blit(self.image["background"], (self.pos['listbackground']), (self.pos['listbackground'], self.size['listbackground'])) # reset background
			if self.playlists:
				for i in range(0,8):
					try:
						listitem = self.playlists[i+self.offset]["playlist"]
					except:
						listitem = ""
					text = self.font["playlist"].render(listitem, 1,(self.color['font']))
					surface.blit(text, (self.pos['list_left'],self.pos['list_top'] + self.size['listitem_height']*int(i)),(0,0, self.pos['list_width'],self.size['listitem_height']))
	
		# Reset updates
		self.resetUpdates()

	# Click handler
	def on_click(self, mousebutton, click_pos):

		# Screen is off and it's touched
		if not self.get_backlight_status() and 0 <= click_pos[0] <= config.resolution[0] and 0 <= click_pos[1] <= config.resolution[1]:
			self.logger.debug("Screen off, screen touch")
			self.backlight_forced_off = False
			self.button(2, mousebutton)

		# Screen is on. Check which button is touched 
		else:
			# There is no multi touch so if one button is pressed another one can't be pressed at the same time

			# Playlists are shown - hide on empty space or button click
			if self.get_playlists_status() or self.get_playlist_status():
			#	if not self.pos['list_left'] <= click_pos[0] <= self.pos['list_right'] or not self.pos['list_top'] <= click_pos[1] <= self.pos['list_bottom']:
				if not self.pos['list_top'] <= click_pos[1] <= self.pos['list_bottom']:
					self.logger.debug("Hiding lists")
					self.button(13, mousebutton)

				# List item clicked
				# List item to select: 4 - 33: 0, 34-63 = 1 etc
				elif self.pos['left'] <= click_pos[0] <= self.pos['list_right'] and self.pos['top'] <= click_pos[1] <= self.pos['list_bottom']:
					list_item = int(floor((click_pos[1] - self.pos['left'])/self.size['listitem_height']))
					if mousebutton == 1:
						self.logger.debug("Selecting list item %s" % list_item)
						self.item_selector(list_item)
					elif mousebutton == 2:
						self.logger.debug("Second-clicked list item %s" % list_item)
			# Selectors
			if self.pos['button_spotify'][0] <= click_pos[0] <= self.pos['button_spotify'][0] + self.size["selectorbutton"] \
			and self.pos['button_spotify'][1] <= click_pos[1] <= self.pos['button_spotify'][1] + self.size["selectorbutton"] \
			and self.pc.mpd and self.pc.spotify:
				self.logger.debug("Switching player")
				self.button(14, mousebutton)
			elif self.pos['button_playlists'][0] <= click_pos[0] <= self.pos['button_playlists'][0] + self.size["selectorbutton"] \
			and self.pos['button_playlists'][1] <= click_pos[1] <= self.pos['button_playlists'][1] + self.size["selectorbutton"] \
			and self.pc.mpd:
				self.logger.debug("Playlists")
				self.button(10, mousebutton)
			elif self.pos['button_cd'][0] <= click_pos[0] <= self.pos['button_cd'][0] + self.size["selectorbutton"] \
			and self.pos['button_cd'][1] <= click_pos[1] <= self.pos['button_cd'][1] + self.size["selectorbutton"] \
			and self.pc.mpd and config.cdda_enabled:
				self.logger.debug("CD")
				self.button(11, mousebutton)
			elif self.pos['button_radio'][0] <= click_pos[0] <= self.pos['button_radio'][0] + self.size["selectorbutton"] \
			and self.pos['button_radio'][1] <= click_pos[1] <= self.pos['button_radio'][1] + self.size["selectorbutton"] \
			and self.pc.mpd and config.radio_playlist:
				self.logger.debug("Radio")
				self.button(12, mousebutton)

			# Toggles
			elif self.pos['button_screenoff'][0] <= click_pos[0] <= config.resolution[0] and self.pos['button_screenoff'][1] <= click_pos[1] <= config.resolution[1]:
				self.logger.debug("Screen off")
				self.backlight_forced_off = True
				self.button(2, mousebutton)
			elif self.pos['button_repeat'][0] <= click_pos[0] <= self.pos['button_repeat'][0] + self.size['togglebutton'][0] \
             and self.pos['button_repeat'][1] <= click_pos[1] <= self.pos['button_repeat'][1] + self.size['togglebutton'][1]:
				self.logger.debug("Toggle repeat") 
				self.button(0, mousebutton)
			elif self.pos['button_random'][0] <= click_pos[0] <= self.pos['button_random'][0] + self.size['togglebutton'][0] \
             and self.pos['button_random'][1] <= click_pos[1] <= self.pos['button_random'][1] + self.size['togglebutton'][1]:
				self.logger.debug("Toggle random")
				self.button(1, mousebutton)

			# Volume
			elif self.pos['button_volumeminus'][0] <= click_pos[0] <= self.pos['button_volumeminus'][0] + self.size['controlbutton'] \
			and self.pos['button_volumeminus'][1] <= click_pos[1] <= self.pos['button_volumeminus'][1] + self.size['controlbutton']:
					if config.volume_enabled:
						self.logger.debug("Volume-")
						self.button(3, mousebutton)
			elif self.pos['button_volumeplus'][0] <= click_pos[0] <= self.pos['button_volumeplus'][0] + self.size['controlbutton'] \
			and self.pos['button_volumeplus'][1] <= click_pos[1] <= self.pos['button_volumeplus'][1] + self.size['controlbutton']:
					if config.volume_enabled:
						self.logger.debug("Volume+")
						self.button(4, mousebutton)

			# Controls
			elif self.pos['button_prev'][0] <= click_pos[0] <= self.pos['button_prev'][0] + self.size['controlbutton'] \
			and self.pos['button_prev'][1] <= click_pos[1] <= self.pos['button_prev'][1] + self.size['controlbutton']:
				self.logger.debug("Prev")
				self.button(6, mousebutton)
			elif self.pos['button_play'][0] <= click_pos[0] <= self.pos['button_play'][0] + self.size['controlbutton'] \
			and self.pos['button_play'][1] <= click_pos[1] <= self.pos['button_play'][1] + self.size['controlbutton']:
				self.logger.debug("Toggle play/pause")
				self.button(7, mousebutton)
			elif self.pos['button_next'][0] <= click_pos[0] <= self.pos['button_next'][0] + self.size['controlbutton'] \
			and self.pos['button_next'][1] <= click_pos[1] <= self.pos['button_next'][1] + self.size['controlbutton']:
				self.logger.debug("Next")
				self.button(8, mousebutton) 

			# Open playlist when longpressing on bottom
			elif self.pos['artist'][1] <= click_pos[1] <= config.resolution[1] and mousebutton == 2:
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
				
			elif number == 7:
				self.pc.control_player("play_pause")

			elif number == 8:
				self.pc.control_player("next")

			elif number == 10:
				self.toggle_playlists()

			elif number == 11:
				self.pc.control_player("cd")
				self.toggle_playlists("False")
				self.toggle_playlist("False")
				self.update_all()

			elif number == 12:
				self.pc.control_player("radio")
				self.toggle_playlist("True")
				self.update_all()
	
			elif number == 13:
				self.toggle_playlists("False")
				self.toggle_playlist("False")

			elif number == 14:
				self.pc.control_player("switch_player")
				self.toggle_playlists("False")
				self.toggle_playlist("False")
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
				self.toggle_playlist("True")

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
					# Check file extension - png, jpg and gif accepted
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
					self.image["cover"] = pygame.transform.scale(coverart, (self.size['coverart'],self.size['coverart']))
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
					subprocess.check_output("wget -q %s -O %s/sp_cover.png" % (coverart_url, "/tmp/"), shell=True )
					self.logger.debug("Spotify coverart downloaded")
					coverart=pygame.image.load("/tmp/" + "sp_cover.png")
					self.logger.debug("Spotify coverart loaded")
					self.image["cover"] = pygame.transform.scale(coverart, (self.size['coverart'],self.size['coverart']))
					self.logger.debug("Spotify coverart placed")
					self.processingCover = False
					self.coverFetched = True
					self.cover = True
			except Exception, e:
				self.logger.exception(e)
				pass

		# No existing coverart, try to fetch from LastFM
		if not self.cover and self.lfm_connected:

			try:
				lastfm_album = self.lfm.get_album(self.artist, self.album)
				self.logger.debug("caT album: %s" % lastfm_album)
			except Exception, e:
				# TODO: Check connection - now it is assumed that there is none if fetching failed
				self.lfm_connected = False
				lastfm_album = {}
				self.logger.exception(e)
				pass

			if lastfm_album:
				try:
					coverart_url = lastfm_album.get_cover_image(2)
					self.logger.debug("caT curl: %s" % coverart_url)
					if coverart_url:
						self.logger.debug("caT sp start")
						subprocess.check_output("wget -q %s -O %s/mpd_cover.png" % (coverart_url, "/tmp/"), shell=True )
						self.logger.debug("caT sp end")
						coverart=pygame.image.load("/tmp/" + "mpd_cover.png")
						self.logger.debug("caT c loaded")
						self.image["cover"] = pygame.transform.scale(coverart, (self.size['coverart'], self.size['coverart']))
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
		if self.backlight:
			self.turn_backlight_off()
		else:
			self.turn_backlight_on()

	def turn_backlight_off(self):
		self.logger.debug("Backlight off")
		subprocess.call("echo '0' > /sys/class/gpio/gpio508/value", shell=True)
		self.backlight = False

	def turn_backlight_on(self):
		self.logger.debug("Backlight on")
		subprocess.call("echo '1' > /sys/class/gpio/gpio508/value", shell=True)
		self.backlight = True

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

		# Clear scroll offset
		self.offset = 0

		if state == "Toggle":
			self.showPlaylists = not self.showPlaylists
		elif state == "True":
			self.showPlaylists = True
		elif state == "False":
			self.showPlaylists = False

		self.logger.debug("Playlists: %s" % self.showPlaylists)

		# Refresh playlists if visible
		if self.showPlaylists:
			self.playlists = self.pc.get_playlists()
	
			# Remove Radio from playlists
			for i in reversed(range(len(self.playlists))):
				if "playlist" in self.playlists[i]:
					if self.playlists[i].get('playlist') == config.radio_playlist:
						self.playlists.pop(i)

		# Ensure that both are not active at the same time
		if self.showPlaylists:
			self.showPlaylist = False

		# Update screen
		self.updateAll = True

	def toggle_playlist(self, state="Toggle"):
	
		# Set offset to point to the current track
		if "pos" in self.pc.song:
			self.offset = int(self.pc.song["pos"])
		else:
			self.offset = 0
	
		if state == "Toggle":
			self.showPlaylist = not self.showPlaylist
		elif state == "True":
			self.showPlaylist = True
		elif state == "False":
			self.showPlaylist = False
		
		self.logger.debug("Playlist: %s" % self.showPlaylist)

		# Refresh playlist if visible
		if self.showPlaylist:
			self.playlist = self.pc.get_playlist()
			
			# Ensure that both are not active at the same time
			self.showPlaylists = False

		# Update screen
		self.update_all()

	def item_selector(self, number):
		if self.showPlaylist and not self.showPlaylists:
			if number + self.offset < len(self.playlist): 
				self.pc.play_item(number + self.offset)
			self.showPlaylist = False
		elif self.showPlaylists and not self.showPlaylist:
			if number + self.offset < len(self.playlists):
				self.pc.load_playlist(self.playlists[number + self.offset]["playlist"])
				self.pc.control_player("play", "mpd")
			self.showPlaylists = False
			#self.pc.control_player("mpd")

		# Update screen
		self.update_all()

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
		if self.get_backlight_status():
			self.screen_timeout_time = datetime.datetime.now() + timedelta(seconds=config.screen_timeout)		
		else:
			self.turn_backlight_on()
