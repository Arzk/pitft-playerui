# -*- coding: utf-8 -*-
import httplib
import logging
import config

class SpotifyControl:
	def __init__(self):	
		self.logger = logging.getLogger("PiTFT-Playerui logger.Spotify control")
		self.status = {}
		self.song   = {}
		self.connection = httplib.HTTPConnection(config.spotify_host, config.spotify_port)
		self.logger.info("Connected to Spotify")

	def refresh(self, active):
		metadata = {}
		try:
			status = self.api(self.connection,"info","status")
			if active:
				metadata = self.api(self.connection,"info","metadata")
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

		if active and bool(metadata):
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
		
			# Check shuffle and repeat state
			if command == "shuffle" and self.status["random"] == 1:
				command += '/disable'
			elif command == "shuffle":
				command += '/enable'
				
			if command == "repeat" and self.status["repeat"] == 1:
				command += '/disable'
				self.status["repeat"] = 0;
			elif command == "repeat":
				command += '/enable'
				self.status["repeat"] = 1;

			#Send command
			self.api(self.connection,"playback", command)

	# Using api from spotify-connect-web
	# Valid methods:  playback, info
	# Valid info commands: metadata, status, image_url/<image_url>, display_name
	# Valid playback commands: play, pause, prev, next, shuffle[/enable|disable], repeat[/enable|disable], volume
	def api(self, client, method, command):
		client.request('GET', '/api/'+method+'/'+command, '{}')
		doc = client.getresponse().read()
		return doc