# -*- coding: utf-8 -*-
import subprocess
from threading import Thread
import time
import os
import glob

from mpd import MPDClient
import pylast

import config
from player_base import PlayerBase

class MPDControl (PlayerBase):
	def __init__(self):
		super(MPDControl, self).__init__("mpd")
		
		self.capabilities["connected"]       = False
		self.capabilities["volume_enabled"]  = config.volume_enabled
		self.capabilities["seek_enabled"]    = True
		self.capabilities["random_enabled"]  = True 
		self.capabilities["repeat_enabled"]  = True
		self.capabilities["elapsed_enabled"] = True
		self.capabilities["library_enabled"] = False
		self.capabilities["logopath"]        = "pics/logo/mpd.png"
	
		self.client = None
		self.noConnection = False		
		self.lfm_connected = False
		
		self.connect()
		
		if self.client:
			self.logger.info("MPD server version: %s" % self.client.mpd_version)

	def refresh(self, active=False):
		status = {}
		song = {}
		
		if not self.client:
			self.connect()
			
		else:
			try:
				status = self.client.status()
				# Check for changes in status
				if status != self.data["status"]:
					if status["state"] != self.data["status"]["state"]:
						self.data["update"]["state"] = True
						# Started playing - request active status
						if status["state"] == "play":
							self.data["update"]["active"] = True
					if status["repeat"] != self.data["status"]["repeat"]:
						self.data["update"]["repeat"]  = True
					if status["random"] != self.data["status"]["random"]:
						self.data["update"]["random"]  = True
					if status["volume"] != self.data["status"]["volume"]:
						self.data["update"]["volume"]  = True
					if status["state"] != "stop":
						if status["elapsed"] != self.data["status"]["elapsed"]:
							self.data["update"]["elapsed"] = True
					else:
						status["elapsed"] = ""
						
					# Save new status
					self.data["status"] = status
						
	
			except Exception as e:
				self.logger.debug(e)
				self._disconnected()
				self.data["status"]["state"]     = ""
				self.data["status"]["elapsed"]   = ""
				self.data["status"]["repeat"]    = ""
				self.data["status"]["random"]    = ""
				self.data["status"]["volume"]    = ""					
	
			try:
				# Fetch song info 
				if active:
					song = self.client.currentsong()
					
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

					# Fetch coverart, but only if we have an album
					if song["album"] and (self.data["song"]["album"] != song["album"]):
						self.logger.debug("MPD coverart changed, fetching...")
						self.data["cover"] = False
		
						# Find cover art on different thread
						try:
							if self.coverartThread:
								if not self.coverartThread.is_alive():
									self.coverartThread = Thread(target=self.fetch_coverart(song))
									self.coverartThread.start()
							else:
								self.coverartThread = Thread(target=self.fetch_coverart(song))
								self.coverartThread.start()
						except Exception, e:
							self.logger.debug("Coverartthread: %s" % e)			
					
					# Check for changes in song
					if song != self.data["song"]:
						if (
								song["artist"] != self.data["song"]["artist"] or
								song["album"]  != self.data["song"]["album"]  or
								song["date"]   != self.data["song"]["date"]   or
								song["track"]  != self.data["song"]["track"]  or
								song["title"]  != self.data["song"]["title"]  or
								song["time"]   != self.data["song"]["time"]
						):
							self.data["update"]["trackinfo"] = True
						if song["album"] != self.data["song"]["album"]:
							self.data["update"]["coverart"] = True
						if song["time"] != self.data["song"]["time"]:
							self.data["update"]["elapsed"] = True
		
						# Save new song info
						self.data["song"] = song
			except Exception as e:
				self.logger.debug(e)
				self._disconnected()
				self.data["song"]["artist"]      = ""
				self.data["song"]["album"]       = ""
				self.data["song"]["date"]        = ""
				self.data["song"]["track"]       = ""
				self.data["song"]["title"]       = ""
				self.data["song"]["time"]        = ""
				self.data["cover"]               = False
				self.data["coverartfile"]        = ""
	
	def connect(self):
		if not self.noConnection:
			self.logger.info("Trying to connect to MPD server")

		client = MPDClient()
		client.timeout = 10
		client.idletimeout = None
		if not self.client:
			 try:
				client.connect(config.mpd_host, config.mpd_port)
				self.client = client
				self.logger.info("Connection to MPD server established.")
				self.noConnection = False
				self.capabilities["connected"]   = True
			 except Exception, e:
				if not self.noConnection:
					self.logger.info(e)
				self._disconnected()
				self.noConnection = True
				self.capabilities["connected"]   = False

		# (re)connect to last.fm
		if not self.lfm_connected and config.API_KEY and config.API_SECRET:
			self.connect_lfm()

	def _disconnected(self):
		# Only print once
		if not self.noConnection:
			self.logger.info("Lost connection to MPD server")
		self.capabilities["connected"]   = False
		self.client = None

	def disconnect(self):
		# Close MPD connection
		if self.client:
			self.client.close()
			self.client.disconnect()
			self.logger.debug("Disconnected from MPD")

	def control(self, command, parameter=-1):
		try:
			if self.client:
				if command == "next":
					self.client.next()
				elif command == "previous":
					self.client.previous()
				elif command == "pause":
					self.client.pause()
				elif command == "play":
					self.client.play()
				elif command == "stop":
					self.client.stop()
				elif command == "rwd":
					self.client.seekcur("-10")
				elif command == "ff":
					self.client.seekcur("+10")
				elif command == "seek" and parameter != -1:
					seektime = parameter*float(self.data["song"]["time"])
					self.client.seekcur(seektime)
				elif command == "repeat":
					repeat = (int(self.data["status"]["repeat"]) + 1) % 2
					self.client.repeat(repeat)
				elif command == "random":
					random = (int(self.data["status"]["random"]) + 1) % 2
					self.client.random(random)
				elif command == "volume" and parameter != -1:
					self.client.setvol(parameter)
		except Exception, e:
			self.logger.info(e)
			self._disconnected()

	def load_playlist(self, command):
		try:
			if self.client:
				self.client.clear()
				self.client.load(command)
		except Exception, e:
			self.logger.info(e)
			self._disconnected()

	def get_playlists(self):
		try:
			if self.client:
				return self.client.listplaylists()
		except Exception, e:
			self.logger.info(e)
			self._disconnected()

	def get_playlist(self):
		try:
			if self.client:
				return self.client.playlistinfo()
		except Exception, e:
			self.logger.info(e)
			self._disconnected()

	def play_item(self, number):
		try:
			if self.client:
				self.client.play(number)
		except Exception, e:
			self.logger.info(e)
			self._disconnected()

	def fetch_coverart(self, song):
		self.data["cover"] = False
		self.data["coverartfile"]=""

		# Search for local coverart
		if "file" in song and config.library_path:

			folder = os.path.dirname(config.library_path + "/" + song["file"])
			coverartfile = ""

			# Get all folder.* files from album folder
			coverartfiles = glob.glob(folder + '/folder.*')

			if coverartfiles:
				self.logger.debug("Found coverart files: %s" % coverartfiles)
				# If multiple found, select one of them
				for file in coverartfiles:
					if file.lower().endswith(('.png', '.jpg', '.jpeg', '.gif')):
						if not coverartfile:
							coverartfile = file
							self.logger.debug("Set coverart: %s" % coverartfile)
						else:
							# Found multiple files. Assume that the largest one has the best quality
							if os.path.getsize(coverartfile) < os.path.getsize(file):
								coverartfile = file
								self.logger.debug("Better coverart: %s" % coverartfile)
				if coverartfile:
					# Image found, load it
					self.logger.debug("Using MPD coverart: %s" % coverartfile)
					self.data["coverartfile"] = coverartfile
					self.data["cover"] = True
					self.data["update"]["coverart"]	= True
				else:
					self.logger.debug("No local coverart file found, switching to Last.FM")

		# No existing coverart, try to fetch from LastFM
		if not self.data["cover"] and self.lfm_connected:

			try:
				lastfm_album = self.lfm.get_album(song["artist"], song["album"])
			except Exception, e:
				self.lfm_connected = False
				lastfm_album = {}
				self.logger.exception(e)
				pass

			if lastfm_album:
				try:
					coverart_url = lastfm_album.get_cover_image(2)
					if coverart_url:
						self.data["coverartfile"] = "/dev/shm/mpd_cover.png"
						subprocess.check_output("wget -q %s -O %s" % (coverart_url, self.data["coverartfile"]), shell=True )
						self.logger.debug("MPD coverart downloaded from Last.fm")
						self.data["cover"] = True
						self.data["update"]["coverart"]	= True
				except Exception, e:
					self.logger.exception(e)
					pass

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