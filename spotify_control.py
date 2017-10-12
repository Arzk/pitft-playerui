# -*- coding: utf-8 -*-
import httplib
import logging
from threading import Thread
import subprocess
import config

class SpotifyControl:
	def __init__(self):	
		self.logger = logging.getLogger("PiTFT-Playerui.Spotify")
		
		self.status = {}
		self.status["state"]  = ""
		self.status["repeat"] = ""
		self.status["random"] = ""
		self.song   = {}
		self.song["artist"]    = ""
		self.song["album"]     = ""
		self.song["title"]     = ""
		self.song["cover_uri"] = ""
		
		self.coverartfile = ""
		self.cover          = False
		self.coverartThread = None

		self.update = {}
		self.update["active"]       = False
		self.update["state"]     	= False
		self.update["elapsed"]   	= False
		self.update["random"]    	= False
		self.update["repeat"]    	= False
		self.update["volume"]    	= False

		self.update["trackinfo"] 	= False
		self.update["coverart"]    	= False
		
		self.client = httplib.HTTPConnection(config.spotify_host, config.spotify_port)
		self.logger.info("Connected to Spotify")

	def refresh(self, active):
		status = {}
		song = {}
		
		try:
			# Fetch status
			sp_status = self._api("info","status")

			# Extract state from strings
			for line in sp_status.split("\n"):
				if "playing" in line:
					status["state"] = "play" if "true" in line else "pause"
				if "shuffle" in line:
					status["random"] = 1 if "true" in line else 0
				if "repeat" in line:
					status["repeat"] = 1 if "true" in line else 0

			# Check for changes in status
			if status != self.status:

				if status["state"] != self.status["state"]:
					self.update["state"]   = True
					# Started playing - request active status
					if status["state"] == "play":
						self.update["active"] = True
				if status["repeat"] != self.status["repeat"]:
					self.update["repeat"]  = True
				if status["random"] != self.status["random"]:
					self.update["random"]  = True

				#Save new status
				self.status = status

			# Fetch song info if active
			if active:
				sp_metadata = self._api("info","metadata")

				# Parse multiline string of type
				# '  "album_name": "Album", '
				# Split lines and remove leading '"' + ending '", '
				for line in sp_metadata.split("\n"):
					if "album_name" in line:
						song["album"] = line.split(": ")[1][1:-3].decode('unicode_escape').encode('utf-8')
					if "artist_name" in line:
						song["artist"] = line.split(": ")[1][1:-3].decode('unicode_escape').encode('utf-8')
					if "track_name" in line:
						song["title"] = line.split(": ")[1][1:-3].decode('unicode_escape').encode('utf-8')
					if "cover_uri" in line:
						song["cover_uri"] = line.split(": ")[1][1:-3]
	
				# Fetch coverart
				if not self.cover or song["cover_uri"] != self.song["cover_uri"]:
					self.logger.debug("Spotify coverart changed, fetching...")
					self.cover = False
				
					# Find cover art on different thread
					try:
						if self.coverartThread:
							if not self.coverartThread.is_alive():
								self.coverartThread = Thread(target=self._fetch_coverart(song["cover_uri"]))
								self.coverartThread.start()
						else:
							self.coverartThread = Thread(target=self._fetch_coverart(song["cover_uri"]))
							self.coverartThread.start()
					except Exception, e:
						self.logger.debug("Coverartthread: %s" % e)
		
				# Check for changes in song
				if song != self.song:
					if ( 
					         song["artist"] != self.song["artist"] or
					         song["album"]  != self.song["album"]  or
					         song["title"]  != self.song["title"]
					):
						self.update["trackinfo"] = True										
					if song["album"] != self.song["album"]:
						self.update["coverart"] = True
	
					# Save new song info
					self.song = song
			
		except Exception as e:
			self.logger.debug(e)

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
#				self.status["repeat"] = 0;
			elif command == "repeat":
				command += '/enable'
#				self.status["repeat"] = 1;

			#Send command
			self._api("playback", command)

	# Using api from spotify-connect-web
	# Valid methods:  playback, info
	# Valid info commands: metadata, status, image_url/<image_url>, display_name
	# Valid playback commands: play, pause, prev, next, shuffle[/enable|disable], repeat[/enable|disable], volume
	def _api(self, method, command):
		self.client.request('GET', '/api/'+method+'/'+command, '{}')
		doc = self.client.getresponse().read()
		return doc

	def _fetch_coverart(self, cover_uri):
		self.cover = False

		try:
			coverart_url = config.spotify_host + ":" + config.spotify_port + "/api/info/image_url/" + cover_uri
			if coverart_url:
				self.coverartfile = "/dev/shm/sp_cover.png"
				subprocess.check_output("wget -q %s -O %s" % (coverart_url, self.coverartfile), shell=True )
				self.logger.debug("Spotify coverart downloaded")
				self.cover = True
		except Exception, e:
			self.logger.exception(e)
			pass