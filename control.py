# -*- coding: utf-8 -*-
import logging
import config
import spotify_control
import mpd_control

class PlayerControl:
	def __init__(self):
		self.logger  = logging.getLogger("PiTFT-Playerui logger.player control")
		self.spotify = None
		self.mpd     = None

		if config.spotify_host and config.spotify_port:
			self.spotify = spotify_control.SpotifyControl()
		if config.mpd_host and config.mpd_port:
			self.mpd = mpd_control.MPDControl()

		# Things to remember
		self.status = {}
		self.song = {}

		# Active player. Determine later
		self.active_player = ""
		
	def determine_active_player(self, old_spotify_status, old_mpd_status):
		try:
			if self.spotify and self.mpd:
				if not self.active_player:
	
					# Spotify playing, MPD not
					if self.spotify.status["state"] == "play" and not self.mpd.status["state"] == "play":
						self.switch_active_player("spotify")
	
					# MPD playing, Spotify not
					elif not self.spotify.status["state"] == "play" and self.mpd.status["state"] == "play":
						self.switch_active_player("mpd")
	
					# Neither playing - default to mpd
					elif not self.spotify.status["state"] == "play" and not self.mpd.status["state"] == "play":
						self.switch_active_player("mpd")
	
					# Both playing - default to mpd and pause Spotify
					else:
						self.switch_active_player("mpd")
						self.control_player("pause", "spotify")
			
				# Started playback - switch and pause other player
				# Spotify started playing - switch
				if self.spotify.status["state"] == "play" and not old_spotify_status == "play" and old_spotify_status:
					self.switch_active_player("spotify")
					if self.mpd.status["state"] == "play":
						self.control_player("pause", "mpd")
						self.logger.debug("Spotify started, pausing mpd")
	
				# MPD started playing - switch
				if self.mpd.status["state"] == "play" and not old_mpd_status == "play" and old_mpd_status:
					self.switch_active_player("mpd")
					if self.spotify.status["state"] == "play":
						self.control_player("pause", "spotify")
						self.logger.debug("mpd started, pausing Spotify")

			elif self.spotify and not self.mpd:
				self.switch_active_player("spotify")

			elif not self.spotify and self.mpd:
				self.switch_active_player("mpd")
				
		except:
				self.switch_active_player("")

	def refresh_players(self):
		
		# Save old status
		try:
			old_spotify_status = self.spotify.status["state"]
			old_mpd_status = self.mpd.status["state"]
		except:
			old_spotify_status = ""
			old_mpd_status = ""

		# Refresh players
		if self.mpd:
			if self.active_player == "mpd":
				self.mpd.refresh(1)
			else:
				self.mpd.refresh(0)

		if self.spotify:
			if self.active_player == "spotify":
				self.spotify.refresh(1)
			else:
				self.spotify.refresh(0)

		# Get active player	
		self.determine_active_player(old_spotify_status, old_mpd_status)

		# Use active player's information
		if self.spotify and self.active_player == "spotify":
			self.status = self.spotify.status
			self.song = self.spotify.song
			
		elif self.mpd and self.active_player == "mpd":
			self.status = self.mpd.status
			self.song = self.mpd.song
		else:
			self.status = {}
			self.song = {}
			
	# Direction: +, -
	def set_volume(self, amount, direction=""):
		if self.mpd and self.active_player == "mpd":
			if direction == "+":
				volume = int(self.status["volume"]) + amount
			elif direction == "-":
				volume = int(self.status["volume"]) - amount
			else:
				volume = amount

			volume = 100 if volume > 100 else volume
			volume = 0 if volume < 0 else volume
			self.mpd.set_volume(volume)
			
	def control_player(self, command, player="active"):
	
		if player == "active":
			player = self.active_player
		if self.status:
			if command == "play_pause":
				if self.status["state"] == "play":
					command = "pause"
				else:
					command = "play"
		
		# Switching commands
		if command == "cd":
			self.play_cd()
		elif command == "radio":
			self.load_playlist(config.radio_playlist)
		elif self.mpd and command == "mpd":
			self.switch_active_player("mpd")
		elif self.spotify and command == "spotify":
			self.switch_active_player("spotify")
		elif command == "switch_player":
			self.switch_active_player("toggle")

		# Player specific commands
		elif player == "spotify":
			self.spotify.control(command)
		elif player == "mpd":
			self.mpd.control(command)

	def load_playlist(self, command):
		self.mpd.load_playlist(command)

	def play_cd(self):
		self.mpd.play_cd()
		
	def get_playlists(self):
		return self.mpd.get_playlists()

	def get_playlist(self):
		return self.mpd.get_playlist()
		
	def play_item(self, number):
		self.mpd.play_item(number)

	def switch_active_player(self, state="toggle"):
		if state == "toggle":
			if self.mpd and self.active_player == "spotify":
				self.active_player = "mpd"
			elif self.spotify and self.active_player == "mpd":
				self.active_player = "spotify"
		else:
			self.active_player = state

	def get_active_player(self):
		return self.active_player