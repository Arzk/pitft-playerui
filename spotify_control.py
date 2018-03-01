# -*- coding: utf-8 -*-
import httplib, urllib
import logging
from threading import Thread
import subprocess
import config

class SpotifyControl:
	def __init__(self):
		self.logger = logging.getLogger("PiTFT-Playerui.Spotify")
		self.client = httplib.HTTPConnection(config.spotify_host, config.spotify_port)
		self.coverartThread = None

		# Capabilities
		self.capabilities = {}
		self.capabilities["name"]            = "spotify"
		self.capabilities["volume_enabled"]  = True
		self.capabilities["seek_enabled"]    = False
		self.capabilities["random_enabled"]  = True 
		self.capabilities["repeat_enabled"]  = True
		self.capabilities["elapsed_enabled"] = False
		self.capabilities["tracknumber_enabled"] = False

		# Things to remember
		self.data = {}
		self.data["status"] = {}
		self.data["status"]["state"]     = ""
		self.data["status"]["repeat"]    = ""
		self.data["status"]["random"]    = ""
		self.data["status"]["volume"]    = ""
		                         
		self.data["song"] = {}           
		self.data["song"]["artist"]      = ""
		self.data["song"]["album"]       = ""
		self.data["song"]["title"]       = ""
		self.data["song"]["cover_uri"]   = ""
                                 
		self.data["coverartfile"]        = ""
		self.data["cover"]               = False

		self.data["update"] = {}
		self.data["update"]["active"]    = False
		self.data["update"]["state"]     = False
		self.data["update"]["elapsed"]   = False
		self.data["update"]["random"]    = False
		self.data["update"]["repeat"]    = False
		self.data["update"]["volume"]    = False
		self.data["update"]["trackinfo"] = False
		self.data["update"]["coverart"]  = False
		
		self.volume = ""

	def __getitem__(self, item):
		return self.data[item]

	def __call__(self, item):
		return self.capabilities[item]

	def refresh(self, active=False):
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
			
			# Get volume from previous metadata
			status["volume"] = self.volume

			# Check for changes in status
			if status != self.data["status"]:

				if status["state"] != self.data["status"]["state"]:
					self.data["update"]["state"]   = True
					# Started playing - request active status
					if status["state"] == "play":
						self.data["update"]["active"] = True
				if status["repeat"] != self.data["status"]["repeat"]:
					self.data["update"]["repeat"]  = True
				if status["random"] != self.data["status"]["random"]:
					self.data["update"]["random"]  = True
				if status["volume"] != self.data["status"]["volume"]:
					self.data["update"]["volume"]  = True

				#Save new status
				self.data["status"] = status
				

			if active:
				# Fetch song info
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
					if "volume" in line:
						self.volume = str(int(line.split(": ")[1])*100/65535)
							
				# Sanity check
				if "artist" not in song:
					song["artist"] = ""
					
				if "album" not in song:
					song["album"] = ""
					
				if "date" not in song:
					song["date"] = ""
					
				if "track" not in song:
					song["track"] = ""
					
				if "title" not in song:
					song["title"] = ""

				if "time" not in song:
					song["time"] = ""
					
				# Fetch coverart
				if song["cover_uri"] and not self.data["cover"] or song["cover_uri"] != self.data["song"]["cover_uri"]:
					self.logger.debug("Spotify coverart changed, fetching...")
					self.data["cover"] = False
	
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
				else:
					song["coverartfile"] = self.data["coverartfile"]
					song["cover"] = self.data["cover"]
	
				# Check for changes in song
				if song != self.data["song"]:
					if (
							song["artist"] != self.data["song"]["artist"] or
							song["album"]  != self.data["song"]["album"]  or
							song["title"]  != self.data["song"]["title"]
					):
						self.data["update"]["trackinfo"] = True
					if song["album"] != self.data["song"]["album"]:
						self.data["update"]["coverart"] = True
										
					# Save new song info
					self.data["song"] = song

		except Exception as e:
			self.logger.debug(e)
					
	def update_ack(self, updated):
		self.data["update"][updated] = False

	def force_update (self,item="all"):
		if item == "all":
			self.data["update"] = dict.fromkeys(self.data["update"], True)
		else:
			self.data["update"][item] = True

	def control(self, command, parameter=-1):
		# Translate commands
		if command == "stop":
			command = "pause"
		if command == "previous":
			command = "prev"
		if command == "random":
			command = "shuffle"
		if command == "volume" and parameter != -1:
			parameter = parameter*65535/100

		# Prevent commands not implemented in api
		if command in ["play", "pause", "prev", "next", "shuffle", "repeat", "volume"]:

			# Check shuffle and repeat state
			if command == "shuffle":
				if self.data["status"]["random"] == 1:
					command += '/disable'
				else:
					command += '/enable'

			if command == "repeat":
				if self.data["status"]["repeat"] == 1:
					command += '/disable'
				else:
					command += '/enable'

			#Send command
			self._api("playback", command, parameter)
			
	def _fetch_coverart(self, cover_uri):
		self.data["cover"] = False
		self.data["coverartfile"] = ""
		try:
			coverart_url = config.spotify_host + ":" + config.spotify_port + "/api/info/image_url/" + cover_uri
			if coverart_url:
				self.data["coverartfile"] = "/dev/shm/sp_cover.png"
				subprocess.check_output("wget -q %s -O %s" % (coverart_url, self.data["coverartfile"]), shell=True )
				self.logger.debug("Spotify coverart downloaded")
				self.data["cover"] = True
				self.data["update"]["coverart"]	= True
		except Exception, e:
			self.logger.exception(e)
			pass

	# Using api from spotify-connect-web
	# Valid methods:  playback, info
	# Valid info commands: metadata, status, image_url/<image_url>, display_name
	# Valid playback commands: play, pause, prev, next, shuffle[/enable|disable], repeat[/enable|disable], volume
	def _api(self, method, command, parameter=0):
		if command != "volume":
			self.client.request('GET', '/api/'+method+'/'+command, '{}')
		else:
			params = urllib.urlencode({"value": parameter})
			headers = {"Content-type": "application/x-www-form-urlencoded", "Accept": "text/plain"}
			self.client.request('POST', '/api/'+method+'/'+command, params, headers)
		doc = self.client.getresponse().read()		
		return doc