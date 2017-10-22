# -*- coding: utf-8 -*-
import time
import logging
import CDDB
import DiscID
import os
import glob
from threading import Thread
import subprocess
from mpd import MPDClient
import pylast
import config

class MPDControl:
	def __init__(self):

		self.logger = logging.getLogger("PiTFT-Playerui.MPD")

		# Pylast
		self.lfm_connected = False

		# MPD Client
		self.logger.info("Setting MPDClient")
		self._connect()

		# Things to remember
		self.status = {}
		self.status["state"]  = ""
		self.status["elapsed"] = ""
		self.status["repeat"] = ""
		self.status["random"] = ""
		self.status["volume"] = ""
		self.song   = {}
		
		self.song["artist"]   = ""
		self.song["album"]    = ""
		self.song["date"]     = ""
		self.song["track"]    = ""
		self.song["title"]    = ""
		self.song["time"]     = ""

		self.cover            = False
		self.coverartfile     = ""
		self.coverartThread   = None

		self.update = {}
		self.update["active"]       = False
		self.update["state"]     	= False
		self.update["elapsed"]   	= False
		self.update["random"]    	= False
		self.update["repeat"]    	= False
		self.update["volume"]    	= False
		self.update["trackinfo"] 	= False
		self.update["coverart"]    	= False

		# CDDA variables
		self.disc_id = {}
		self.cdda_artist_album = {}
 		self.cdda_query_status = {}
		self.cdda_query_info = {}
		self.cdda_read_status = {}
		self.cdda_read_info = {}

		# Print data
		self.logger.info("MPD server version: %s" % self.mpdc.mpd_version)

	def refresh(self):
		status = {}
		song = {}

		try:
			status = self.mpdc.status()

			# Check for changes in status
			if status != self.status:
				if status["state"] != self.status["state"]:
					self.update["state"] = True
					# Started playing - request active status
					if status["state"] == "play":
						self.update["active"] = True
				if status["repeat"] != self.status["repeat"]:
					self.update["repeat"]  = True
				if status["random"] != self.status["random"]:
					self.update["random"]  = True
				if status["volume"] != self.status["volume"]:
					self.update["volume"]  = True
				if status["state"] != "stop":
					if status["elapsed"] != self.status["elapsed"]:
						self.update["elapsed"] = True
				else:
					status["elapsed"] = ""
				# Save new status
				self.status = status

			# Fetch song info 
			song = self.mpdc.currentsong()
			if song:
				# Read CDDB if playing CD
				if "file" in song and config.cdda_enabled:
					if "cdda://" in song["file"]:
						song=self._refresh_cd(song)
	
				# Fetch coverart
				if not self.cover or self.song["album"] != song["album"]:
					self.logger.debug("MPD coverart changed, fetching...")
					self.cover = False
	
					# Find cover art on different thread
					try:
						if self.coverartThread:
							if not self.coverartThread.is_alive():
								self.coverartThread = Thread(target=self._fetch_coverart(song))
								self.coverartThread.start()
						else:
							self.coverartThread = Thread(target=self._fetch_coverart(song))
							self.coverartThread.start()
					except Exception, e:
						self.logger.debug("Coverartthread: %s" % e)
	
				# Check for changes in song
				if song != self.song:
					if (
							song["artist"] != self.song["artist"] or
							song["album"]  != self.song["album"]  or
							song["date"]   != self.song["date"]   or
							song["track"]  != self.song["track"]  or
							song["title"]  != self.song["title"]  or
							song["time"]   != self.song["time"]
					):
						self.update["trackinfo"] = True
					if song["album"] != self.song["album"]:
						self.update["coverart"] = True
					if song["time"] != self.song["time"]:
						self.update["coverart"] = True
						self.updateElapsed = True
	
					# Save new song info
					self.song = song

		except Exception as e:
			self.logger.debug(e)

	def _connect(self):
		self.logger.info("Trying to connect to MPD server")

		client = MPDClient()
		client.timeout = 10
		client.idletimeout = None
		noConnection = True

		while noConnection:
			try:
				client.connect(config.mpd_host, config.mpd_port)
				noConnection=False
			except Exception, e:
				self.logger.info(e)
				noConnection=True
				time.sleep(5)
		self.mpdc = client
		self.logger.info("Connection to MPD server established.")

		# (re)connect to last.fm
		if not self.lfm_connected and config.API_KEY and config.API_SECRET:
			self._connect_lfm()

	def _disconnect(self):
		# Close MPD connection
		if self.mpdc:
			self.mpdc.close()
			self.mpdc.disconnect()
			self.logger.debug("Disconnected from MPD")

	def _refresh_cd(self, song):

		# CDDB query not done - do it now
		if not self.cdda_read_info:
			self.load_cd()

		# Fill song information from CD
		# Artist
		try:
			song["artist"] = self.cdda_artist_album[0]
		except:
			song["artist"] = ""
		# Album
		try:
			song["album"] = self.cdda_artist_album[1]
		except:
			song["album"] = ""
		# Date
		try:
			song["date"] = self.cdda_read_info["DYEAR"]
		except:
			song["date"] = ""
		# Track Number
		try:
			# Get filename from mpd
			song["track"] = song["file"].split("cdda:///")[-1].split()[0]
		except:
			song["track"] = ""
		# Title
		try:
			number=int(song["track"]) - 1
			song["title"] = self.cdda_read_info["TTITLE" + str(number)]
		except:
			song["title"] = ""
		# Time
		try:
			if int(song["track"]) == int(self.disc_id[1]):
				# The final track has to be counted with
				# CD length in seconds - start frame of final track
				# 75 frames = 1 second
				song["time"] = self.disc_id[int(song["track"]) + 2] - self.disc_id[int(song["track"]) + 1] / 75
			else:
				# For other tracks count from start frame of track and next track.
				song["time"] = (self.disc_id[int(song["track"]) + 2] - self.disc_id[int(song["track"]) + 1]) / 75
		except:
			song["time"] = 0

		return song

	# Direction: +, -
	def set_volume(self, volume):
		self.mpdc.setvol(volume)

	def control(self, command):
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
		elif command == "repeat":
			repeat = (int(self.status["repeat"]) + 1) % 2
			self.mpdc.repeat(repeat)
		elif command == "random":
			random = (int(self.status["random"]) + 1) % 2
			self.mpdc.random(random)

	def load_playlist(self, command):
		self.mpdc.clear()
		self.mpdc.load(command)

	def _query_cddb(self, disc_id):

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
				self.cdda_artist_album = self.cdda_read_info["DTITLE"].split(" / ")
			except:
				self.cdda_artist_album = {};
		else:
			self.logger.info("CDDB read failed, status: %s" % self.cdda_read_status)

	def load_cd(self):
		try:
			cdrom = DiscID.open()
			disc_id = DiscID.disc_id(cdrom)
		except:
			disc_id = {}
		if disc_id:
			self.logger.debug("Loaded new cd, id: %s" % disc_id)
			self._query_cddb(disc_id)
		return disc_id

	def play_cd(self):
		self.disc_id = self.load_cd()
		if self.disc_id:
			self.logger.info("Playing CD")
			self.mpdc.clear()
			number_of_tracks = int(self.disc_id[1])
			for i in range (1, number_of_tracks):
				self.mpdc.add("cdda:///" + str(i))

			self.mpdc.random(0)
			self.mpdc.repeat(0)
			self.mpdc.play()
		else:
			self.logger.info("No CD found")

	def get_playlists(self):
		return self.mpdc.listplaylists()

	def get_playlist(self):
		return self.mpdc.playlistinfo()

	def play_item(self, number):
		self.mpdc.play(number)

	def _fetch_coverart(self, song):
		self.cover = False
		self.coverartfile=""

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
					self.logger.debug("Using MPD coverart: %s" % coverartfile)
					self.coverartfile = coverartfile
					self.cover = True
					self.update["coverart"]	= True
				else:
					self.logger.debug("No local coverart file found, switching to Last.FM")

		# No existing coverart, try to fetch from LastFM
		if not self.cover and self.lfm_connected:

			try:
				lastfm_album = self.lfm.get_album(song["artist"], song["file"])
			except Exception, e:
				self.lfm_connected = False
				lastfm_album = {}
				self.logger.exception(e)
				pass

			if lastfm_album:
				try:
					coverart_url = lastfm_album.get_cover_image(2)
					if coverart_url:
						self.coverartfile = "/dev/shm/mpd_cover.png"
						subprocess.check_output("wget -q %s -O %s" % (coverart_url, self.coverartfile), shell=True )
						self.logger.debug("MPD coverart downloaded from Last.fm")
						self.cover = True
						self.update["coverart"]	= True
				except Exception, e:
					self.logger.exception(e)
					pass

		# Processing finished
		self.processingCover = False

	def _connect_lfm(self):
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

