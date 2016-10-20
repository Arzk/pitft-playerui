# -*- coding: utf-8 -*-
import time
import logging
import CDDB
import DiscID
import config
from mpd import MPDClient

class MPDControl:
	def __init__(self):

		self.logger = logging.getLogger("PiTFT-Playerui logger.MPD control")
	
		# MPD Client
		self.logger.info("Setting MPDClient")
		self.reconnect = False
		self.connect()

		# Things to remember
		self.status = {}
		self.song = {}
	
		# CDDA variables
		self.disc_id = {}
		self.cdda_artist_album = {}
 		self.cdda_query_status = {}
		self.cdda_query_info = {}
		self.cdda_read_status = {}
		self.cdda_read_info = {}

		# Print data
		self.logger.info("MPD server version: %s" % self.mpdc.mpd_version)
		
	def connect(self):
		if self.reconnect:
			self.logger.info("Reconnecting to MPD server")
		else:
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
		self.reconnect = False
		self.logger.info("Connection to MPD server established.")
		
	def disconnect(self):
		# Close MPD connection
		if self.mpdc:
			self.mpdc.close()
			self.mpdc.disconnect()
			self.logger.debug("Disconnected from MPD")		
					
	def refresh(self,active):
		if self.reconnect:
			self.connect()
		if self.reconnect == False:
			connection = False
			try:
				self.status = self.mpdc.status()
				if active:
					self.song = self.mpdc.currentsong()
				connection = True

				# Read CDDB if playing CD
				if "file" in self.song and config.cdda_enabled:
					if "cdda://" in self.song["file"]:
						self.refresh_cd()

			except Exception as e:
				self.logger.debug(e)
				connection = False
				self.status = {}
				self.song = {}

			if connection == False:
				try:
					if e.errno == 32:
						self.reconnect = True
					else:
						print "Nothing to do"
				except Exception, e:
					self.reconnect = True
					self.logger.debug(e)

	def refresh_cd(self):
		# Get filename from mpd
		try:
			file = self.song["file"]
		except:
			file = "";
		
		# CDDB query not done - do it now
		if not self.cdda_read_info:
			self.load_cd()
	
		# Fill song information from CD	
		# Artist
		try:
			self.song["artist"] = self.cdda_artist_album[0]
		except:
			self.song["artist"] = ""
		# Album
		try:
			self.song["album"] = self.cdda_artist_album[1]
		except:
			self.song["album"] = ""
		# Date
		try:
			self.song["date"] = self.cdda_read_info["DYEAR"]
		except:
			self.song["date"] = ""
		# Track Number
		try:
			self.song["track"] = file.split("cdda:///")[-1].split()[0]
		except:
			self.song["track"] = file.split("cdda:///")[-1].split()[0]
		# Title
		try:
			number=int(self.song["track"]) - 1
			self.song["title"] = self.cdda_read_info["TTITLE" + str(number)]
		except:
			self.song["title"] = ""
		# Time
		try:
			if int(self.song["track"]) == int(self.disc_id[1]):
				# The final track has to be count with 
				# CD length in seconds - start frame of final track
				# 75 frames = 1 second
				self.song["time"] = self.disc_id[int(self.song["track"]) + 2] - self.disc_id[int(self.song["track"]) + 1] / 75
			else:
				# For other tracks count from start frame of track and next track.
				self.song["time"] = (self.disc_id[int(self.song["track"]) + 2] - self.disc_id[int(self.song["track"]) + 1]) / 75
		except:
			self.song["time"] = 0
		
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

	def query_cddb(self, disc_id):
	
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
			self.query_cddb(disc_id)
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
