# -*- coding: utf-8 -*-
import httplib
import logging
import config

class SpotifyControl:
	def __init__(self):	
		self.logger = logging.getLogger("PiTFT-Playerui logger.Spotify control")
		self.status = {}
		self.song   = {}

	def refresh(self):
		try:
			status = self.api("info","status")
			metadata = self.api("info","metadata")
		except:
			status = {}
			metadata = {}

		self.status["active"] = False
		
		# Extract state from strings
		if status:
			for line in status.split("\n"):
				# Active device in Spotify
				if "active" in line:
					if "true" in line:
						self.status["active"] = True
					else:
						self.status["active"] = False
				if "playing" in line:
					if "true" in line and self.status["active"]:
						self.status["state"] = "play"
					else:
						self.status["state"] = "pause"
				if "shuffle" in line:
					if "true" in line and self.status["active"]:
						self.status["random"] = 1
					else:
						self.status["random"] = 0
				if "repeat" in line:
					if "true" in line and self.status["active"]:
						self.status["repeat"] = 1
					else:
						self.status["repeat"] = 0

		if metadata and self.status["active"]:
			# Parse multiline string of type
			# '  "album_name": "Album", '
			# Split lines and remove leading '"' + ending '", '
			for line in metadata.split("\n"):
				if "album_name" in line:
					self.song["album"] = line.split(": ")[1][1:-3].decode('unicode_escape').encode('utf-8')
				if "artist_name" in line:
					self.song["artist"] = line.split(": ")[1][1:-3].decode('unicode_escape').encode('utf-8')
				if "track_name" in line:
					self.song["title"] = line.split(": ")[1][1:-3].decode('unicode_escape').encode('utf-8')
#					self.logger.debug(type(self.song["title"]))
					self.logger.debug(self.song["title"])
				if "cover_uri" in line:
					self.song["cover_uri"] = line.split(": ")[1][1:-3]
		else:
			self.song = {}
					
	def control(self, command):
		# Translate commands
		if command == "stop":
			command = "pause"
		if command == "previous":
			command = "prev"
		if command == "random":
			command = "shuffle"

		# Prevent commands not implemented in api
		if command in ["play", "pause", "prev", "next", "shuffle", "repeat"]:
			self.api("playback", command)

	# Using api from spotify-connect-web
	# Valid methods:  playback, info
	# Valid info commands: metadata, status, image_url/<image_url>, display_name
	# Valid playback commands: play, pause, prev, next, shuffle, repeat, volume
	def api(self, method, command):
		c = httplib.HTTPConnection(config.spotify_host, config.spotify_port)
		c.request('GET', '/api/'+method+'/'+command, '{}')
		doc = c.getresponse().read()
		return doc