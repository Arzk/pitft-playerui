# -*- coding: utf-8 -*-
import logging

class PlayerBase(object):
	def __init__(self, name):
		self.logger = logging.getLogger("PiTFT-Playerui." + name)
		self.coverartThread = None

		# Capabilities
		self.capabilities = {
					"name"            : name,
					"connected"       : False,
					"volume_enabled"  : False,
					"seek_enabled"    : False,
					"random_enabled"  : False, 
					"repeat_enabled"  : False,
					"elapsed_enabled" : False,
					"library_enabled" : False,
					"logopath"        : ""
					}

		# Things to remember
		self.data = {
					"status" : {
					           "state"       : "",
					           "elapsed"     : "",
					           "repeat"      : "",
					           "random"      : "",
					           "volume"      : ""
							   },
					"song" :   {
		                       "artist"      : "",
		                       "album"       : "",
		                       "date"        : "",
		                       "track"       : "",
		                       "title"       : "",
		                       "time"        : "",
		                       "cover_uri"   : ""
							   },
                                      
		            "cover"                  : False,
		            "coverartfile"           : "",
					"update" : {
							   "active"      : False,
							   "state"       : False,
							   "elapsed"     : False,
							   "random"      : False,
							   "repeat"      : False,
							   "volume"      : False,
							   "trackinfo"   : False,
							   "coverart"    : False
								} 		
					} 		
		
	def __getitem__(self, item):
		return self.data[item]
		
	def __call__(self, item):
		return self.capabilities[item]
		
	def refresh(self, active=False):
		pass

	def force_update (self,item="all"):
		if item == "all":
			self.data["update"] = dict.fromkeys(self.data["update"], True)
		else:
			self.data["update"][item] = True
		
	def update_ack(self, updated):
		self.data["update"][updated] = False

	def control(self, command, parameter=-1):
		pass
		