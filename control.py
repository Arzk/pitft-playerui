# -*- coding: utf-8 -*-
import logging
import config
from spotify_control import SpotifyControl
from mpd_control import MPDControl
from cd_control import CDControl

class PlayerControl:
	def __init__(self):
		self.logger  = logging.getLogger("PiTFT-Playerui.Player_Control")
		self.spotify = None
		self.mpd     = None
		self.cd      = None
		# Active player. Determine later
		self.active_player = None

		try:
			self.logger.debug("Setting Spotify")
			if config.spotify_host and config.spotify_port:
				self.spotify = SpotifyControl()
		except Exception, e:
			self.logger.debug(e)
		try:
			self.logger.debug("Setting MPD")
			if config.mpd_host and config.mpd_port:
				self.mpd = MPDControl()
		except Exception, e:
			self.logger.debug(e)
		try:
			self.logger.debug("Setting CD")
			if config.cdda_enabled:
				self.cd = CDControl()
		except Exception, e:
			self.logger.debug(e)

		try:
			if self.mpd:
				self.active_player = self.mpd
			elif self.spotify:
				self.active_player = self.spotify
			elif self.cd:
				self.active_player = self.cd
			else:
			    raise Exception("No players defined in config")
		except Exception, e:
			self.logger.debug(e)
			raise
		self.logger.debug("Player control set")
		
	def __getitem__(self, item):
		if self.active_player:
			return self.active_player[item]
		else:
			return {}

	def __call__(self, item):
		return self.active_player(item)
		
	def determine_active_player(self):

		if self.spotify and self.mpd:
			# Spotify playing
			if self.spotify["update"]["active"]:
				self.logger.debug("Spotify started")
				self.switch_active_player("spotify")
				if self.mpd:
					if self.mpd["status"]["state"] == "play":
						self.control_player("pause", "mpd")
						self.logger.debug("Pausing mpd")

			# MPD playing
			if self.mpd["update"]["active"]:
				self.logger.debug("mpd started")
				self.switch_active_player("mpd")
				if self.spotify["status"]["state"] == "play":
					self.control_player("pause", "spotify")
					self.logger.debug("Pausing Spotify")

	def refresh(self, active):

		# Refresh players, get only status if not active
		if self.mpd:
			self.mpd.refresh(self.active_player("name") == "mpd")
		if self.spotify:
			self.spotify.refresh(self.active_player("name") == "spotify")
		if self.cd:
			self.cd.refresh(self.active_player("name") == "cd")

		# Get active player
		self.determine_active_player()

	def update_ack(self, updated):
		self.active_player.update_ack(updated)
		
	# Direction: +, -
	def set_volume(self, amount, direction=""):
		if self.active_player("volume_enabled"):
			if direction == "+":
				volume = int(self.active_player["status"]["volume"]) + amount
			elif direction == "-":
				volume = int(self.active_player["status"]["volume"]) - amount
			else:
				volume = amount

			volume = 100 if volume > 100 else volume
			volume = 0 if volume < 0 else volume
			self.active_player.set_volume(volume)

	def control_player(self, command, player="active", parameter=0):
		if self.active_player["status"]:
			if command == "play_pause":
				if self.active_player["status"]["state"] == "play":
					command = "pause"
				else:
					command = "play"

		# Switching commands
		if command == "radio":
			self.load_playlist(config.radio_playlist)
		elif self.mpd and command == "mpd":
			self.switch_active_player("mpd")
		elif self.spotify and command == "spotify":
			self.switch_active_player("spotify")
		elif self.cd and command == "cd":
			self.switch_active_player("cd")

		# Player specific commands
		elif player == "spotify":
			self.spotify.control(command, parameter)
		elif player == "mpd":
			self.mpd.control(command, parameter)
		elif player == "active":
			self.active_player.control(command, parameter)

	def load_playlist(self, command):
		self.mpd.load_playlist(command)

	def get_playlists(self):
		return self.mpd.get_playlists()

	def get_playlist(self):
		return self.mpd.get_playlist()

	def play_item(self, number):
		self.mpd.play_item(number)

	def switch_active_player(self, player):
		player_changed = False
		if player == "mpd" and self.active_player("name") != "mpd":
			player_changed = True
			self.active_player = self.mpd
			self.logger.debug("Switching player to MPD")
		elif player == "spotify" and self.active_player("name") != "spotify":
			player_changed = True
			self.active_player = self.spotify
			self.logger.debug("Switching player to Spotify")
		elif player == "cd" and self.active_player("name") != "cd":
			player_changed = True
			self.active_player = self.cd
			self.logger.debug("Switching player to CD")
		if player_changed:
			self.active_player.force_update()
		
		# Ack the request
		self.active_player.update_ack("active")

	def get_active_player(self):
		return self.active_player