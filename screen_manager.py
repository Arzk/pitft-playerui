# -*- coding: utf-8 -*-
import sys, pygame
from pygame.locals import *
import time
import logging
import subprocess
import os
import glob
import re
from math import ceil, floor
import datetime
from datetime import timedelta

import config
from control import PlayerControl
from positioning import *

class ScreenManager:
	def __init__(self, path):
		self.logger = logging.getLogger("PiTFT-Playerui.Screen_Manager")
		self.pc = PlayerControl()

		# Paths
		#path = os.path.dirname(os.path.abspath(__file__)) + "/"
		os.chdir(path)

		# Fonts
		try:
			self.fontfile = config.fontfile
			self.font = {}
			self.font["menuitem"]    = pygame.font.Font(self.fontfile, 20)
			self.font["details"]     = pygame.font.Font(self.fontfile, 16)
			self.font["elapsed"]     = pygame.font.Font(self.fontfile, 16)
			self.font["listview"]    = pygame.font.Font(self.fontfile, 20)
			self.font["field"]       = pygame.font.Font(self.fontfile, 20)
		except Exception, e:
			self.logger.debug(e)
			raise
	
		# Images
		try:
			self.image = {}
			self.image["background"]             = pygame.image.load("pics/" + "background.png")
			
			self.image["coverart_place"]         = pygame.image.load("pics/" + "coverart-placer.png")
			self.image["coverart_border_clean"]  = pygame.image.load("pics/" + "coverart-border.png")
			self.image["coverart_border_paused"] = pygame.image.load("pics/" + "coverart-paused.png")
			self.image["coverart_border_next"]   = pygame.image.load("pics/" + "coverart-next.png")
			self.image["coverart_border_prev"]   = pygame.image.load("pics/" + "coverart-previous.png")

			self.image["cover"]                  = self.image["coverart_place"]
			self.image["coverart_border"]        = self.image["coverart_border_clean"]

			self.image["progress_bg"]            = pygame.image.load("pics/" + "position-background.png")
			self.image["progress_fg"]            = pygame.image.load("pics/" + "position-foreground.png")
			self.image["volume_bg"]              = pygame.image.load("pics/" + "volume_bg.png")
			self.image["volume_fg"]              = pygame.image.load("pics/" + "volume_fg.png")
                                                
			self.image["button_repeat_off"]	     = pygame.image.load("pics/" + "button-repeat-off.png")
			self.image["button_repeat_on"]	     = pygame.image.load("pics/" + "button-repeat-on.png")
			self.image["button_repeat"]	         = self.image["button_repeat_off"]
			self.image["button_random_off"]	     = pygame.image.load("pics/" + "button-random-off.png")
			self.image["button_random_on"]	     = pygame.image.load("pics/" + "button-random-on.png")
			self.image["button_random"]	         = self.image["button_repeat_off"]

		except Exception, e:
			self.logger.debug(e)
			raise
		
		# Things to show
		self.status = {}
		self.status["artist"]          = ""
		self.status["album"]           = ""
		self.status["artistalbum"]     = ""
		self.status["date"]            = ""
		self.status["track"]           = ""
		self.status["title"]           = ""
		self.status["file"]            = ""
		self.status["timeElapsed"]     = "00:00"
		self.status["timeTotal"]       = "00:00"
		self.status["timeElapsedPercentage"] = 0
		self.status["playbackStatus"]  = "stop"
		self.status["volume"]          = 0
		self.status["random"]          = 0
		self.status["repeat"]          = 0
		
		self.status["update"] = {}
		self.status["update"]["screen"]    = True
		self.status["update"]["state"]     = True
		self.status["update"]["elapsed"]   = True
		self.status["update"]["random"]    = True
		self.status["update"]["repeat"]    = True
		self.status["update"]["volume"]    = True
		self.status["update"]["trackinfo"] = True
		self.status["update"]["coverart"]  = True

		self.listcontent = None
		self.listclick   = None
		
		# Visual indicators when scrolling on sliders
		self.seekpos = -1.0
		self.volumepos = -1
		
		self.view = "main"
		self.offset             = 0,0
		self.draw_offset        = 0,0
		self.list_offset        = 0
		self.num_listitems = config.resolution[1]//size["listitem_height"]
		
		self.turn_backlight_on()
		self.populate_players()
		self.logger.debug("Init done")
		self.first_refresh_done = False
		
	def populate_players(self):
		self.topmenu = []
		self.playerlogos = []
		players = self.pc.get_players()
		for player in players:
			try:
				self.topmenu.append(player.get('name'))
				logopath = player.get('logopath')
				if logopath:
					self.playerlogos.append(pygame.transform.scale(pygame.image.load(logopath), size["logo"]))
					self.logger.debug(logopath)
				else: 
					self.playerlogos.append(None)
			except Exception, e:
				self.logger.debug(e)

	def refresh(self, active):

		# Update screen timeout if there was any user activity
		if active and config.screen_timeout > 0:
			self.update_screen_timeout()

		# Refresh information from players
		try:
			self.pc.refresh(self.first_refresh_done)
		except Exception, e:
			self.logger.debug(e)
			raise
		
		# Parse new song information
		try:
			self.parse_song()
		except Exception, e:
			self.logger.debug(e)
			pass
		
		# Something is playing - keep screen on
		if self.pc["status"] and config.screen_timeout > 0 and not self.backlight_forced_off:
			if self.pc["status"]["state"] == "play":
				self.update_screen_timeout()
				active = True

			# Nothing playing for n seconds, turn off screen if not already off
			elif self.screen_timeout_time < datetime.datetime.now() and self.backlight:
				self.turn_backlight_off()
				active = False
		self.first_refresh_done = True
		return active

	def parse_song(self):

		# State icons on cover art
		if self.pc["update"]["state"]:
			if self.pc["status"]["state"] == "play":
				self.image["coverart_border"] = self.image["coverart_border_clean"]
			else:
				self.image["coverart_border"] = self.image["coverart_border_paused"]

			self.force_update("state")
			self.force_update("coverart")
			self.pc.update_ack("state")
			
		if self.pc["update"]["elapsed"]:
		
			# Time elapsed
			try:
				min = int(ceil(float(self.pc["status"]["elapsed"])))/60
				min = min if min > 9 else "0%s" % min
				sec = int(ceil(float(self.pc["status"]["elapsed"])%60))
				sec = sec if sec > 9 else "0%s" % sec
				self.status["timeElapsed"] = "%s:%s" % (min,sec)
			except:
				self.status["timeElapsed"] = ""
			
			# Time elapsed percentage
			try:
				self.status["timeElapsedPercentage"] = float(self.pc["status"]["elapsed"])/float(self.pc["song"]["time"])
			except:
				self.status["timeElapsedPercentage"] = 0
		
			self.force_update("elapsed")	
			self.pc.update_ack("elapsed")
			
		if self.pc["update"]["trackinfo"]:
		
			# Position
			try:
				self.status["pos"] = self.pc["song"]["pos"]
			except:
				self.status["pos"] = ""
				
			try:
				self.status["artist"] = self.pc["song"]["artist"].decode('utf-8')
			except:
				self.status["artist"] = ""
				
			# Album
			try:
				self.status["album"] = self.pc["song"]["album"].decode('utf-8')
			except:
				self.status["album"] = ""
				
			# Artist - Album
			if self.status["artist"]:
				self.status["artistalbum"] = self.status["artist"]
				if self.status["album"]:
					self.status["artistalbum"] += " - "
			else:
				self.status["artistalbum"] = ""
			self.status["artistalbum"] += self.status["album"]

			# Date
			try:
				self.status["date"] = self.pc["song"]["date"].decode('utf-8')
			except:
				self.status["date"] = ""

			# Append: Artist - Album (date)
			if self.status["date"]:
				self.status["artistalbum"] += " (" + self.status["date"] + ")"

			# Track number
			try:
				self.status["track"] = self.pc["song"]["track"].decode('utf-8')
			except:
				self.status["track"] = ""
				
			# Title
			try:
				if self.pc["song"]["title"]:
					self.status["title"] = self.pc["song"]["title"].decode('utf-8')
				else:
					self.status["title"] = self.pc["song"]["file"].decode('utf-8')
			except:
				self.status["title"] = ""

			if self.status["track"]:
				self.status["title"] = self.status["track"] + " - " + self.status["title"]
			
			# Time total
			try:
				min = int(ceil(float(self.pc["song"]["time"])))/60
				sec = int(ceil(float(self.pc["song"]["time"])%60))
				min = min if min > 9 else "0%s" % min
				sec = sec if sec > 9 else "0%s" % sec
				self.status["timeTotal"] = "%s:%s" % (min,sec)
			except:
				self.status["timeTotal"] = ""
				
			self.force_update("trackinfo")
			self.pc.update_ack("trackinfo")

		if self.pc["update"]["random"]:
			try:
				self.status["random"] = int(self.pc["status"]["random"])
			except:
				self.status["random"] = 0

			if self.status["random"]:
				self.image["button_random"] = self.image["button_random_on"]
			else:
				self.image["button_random"] = self.image["button_random_off"]
			
			self.force_update("random")	
			self.pc.update_ack("random")
			
		if self.pc["update"]["repeat"]:
			try:
				self.status["repeat"] = int(self.pc["status"]["repeat"])
			except:
				self.status["repeat"] = 0
			if self.status["repeat"]:
				self.image["button_repeat"] = self.image["button_repeat_on"]
			else:
				self.image["button_repeat"] = self.image["button_repeat_off"]
			
			self.force_update("repeat")	
			self.pc.update_ack("repeat")
			
		if self.pc["update"]["volume"]:
			try:
				self.status["volume"] = int(self.pc["status"]["volume"])
			except:
				self.status["volume"] = 0

			self.force_update("volume")
			self.pc.update_ack("volume")

		if self.pc["update"]["coverart"]:
			self.image["cover"] = self.fetch_coverart(self.pc["coverartfile"])

			self.force_update("coverart")
			self.pc.update_ack("coverart")
				
	def fetch_coverart(self, coverartfile):
		if coverartfile:
			try:
				self.logger.debug("Using coverart: %s" % coverartfile)
				coverart = pygame.image.load(coverartfile)
				return pygame.transform.scale(coverart, size["coverart"])
			except Exception, e:
				self.logger.exception(e)
				return self.image["coverart_place"]
		else:
			return self.image["coverart_place"]
			
	def render(self, surface):
		if self.updated("screen"):
			surface.blit(self.image["background"], (0,0))

		try:
			if self.view == "main":
				self.render_mainscreen(surface)
			elif self.view == "listview":
				self.render_listview(surface)
		except Exception, e:
			self.logger.debug(e)
			pass
	
	def on_click(self, mousebutton, clickpos):
		try:
			self.logger.debug("Click: " + str(mousebutton) + " X: " + str(clickpos[0]) + " Y: " + str(clickpos[1]))
			if self.view == "main":
				allow_repeat = self.on_click_mainscreen(mousebutton, clickpos)
			elif self.view == "listview":
				allow_repeat = self.on_click_listview(mousebutton, clickpos)
		except Exception, e:
			self.logger.debug(e)
			allow_repeat = False
			pass
		return allow_repeat

	def on_scroll(self, start, x, y, end=False):
		# Update total offset
		self.offset = (self.offset[0] + x, self.offset[1] + y)
		
		# Screen specific
		if self.view == "main":
			self.scroll_mainscreen(start, self.offset[0], self.offset[1], end)
		elif self.view == "listview":
			self.scroll_listview(start, self.offset[0], self.offset[1], end)
			
		# Scroll ended
		if end:
			self.offset = 0,0

		# Redraw screen
		self.force_update("screen")
			
	def switch_view(self, view, items=None):
		# Update everything
		self.status["update"]["screen"]    = True
		# Ensure that the pointers are ok for lists
		if view == "listview":
			self.list_offset = 0
			self.listcontent = items.get("content", None)
			self.listclick = items.get("clickfunc", None)
			if self.listcontent and self.listclick:
				self.view=view
		else:
			self.view="main"
		self.force_update()

	def render_mainscreen(self,surface):

		# Menus
		if self.updated("screen"):
		
			# Update everything
			self.force_update()
		
			# Bottom menu
			for index, item in enumerate(self.pc.get_menu()):
				color = "text" if self.draw_offset[1] == -(index+1)*size["bottommenu"] else "inactive"
				text = render_text(item["name"], self.font["menuitem"], color)			
				text_rect = text.get_rect(center=(config.resolution[0]/2, 0))
				surface.blit(text,
							menupos("bottommenu", index, (text_rect[0],self.draw_offset[1]))) 
			# Top menu
			# TODO: Don't refresh every cycle, but find a way to skip disconnected players
			# self.topmenu = self.pc.get_player_names()
			for i in range (0,len(self.topmenu)-1):
				index = i if i < self.pc.get_current() else i+1
				color = "text" if self.draw_offset[1] == (i+1)*size["topmenu"] else "inactive"
				text = render_text(self.topmenu[index], self.font["menuitem"], color)
				text_rect = text.get_rect(center=(config.resolution[0]/2, 0))
				surface.blit(text,
							menupos("topmenu", i, (text_rect[0],self.draw_offset[1]), "up")) 
			self.update_ack("screen")

		# Track info
		if self.updated("trackinfo"):
			# Refresh backgrounds
			surface.blit(self.image["background"], 
						pos("trackinfobackground",(0,self.draw_offset[1])), 
						(pos("trackinfobackground",(0,self.draw_offset[1])),
						size["trackinfobackground"]))
			surface.blit(self.image["progress_bg"], 
						pos("progressbar", (0,self.draw_offset[1])))

			# Artist - Album (date)
			surface.blit(render_text(self.status["artistalbum"], self.font["details"]),
						pos("album", (0,self.draw_offset[1])))
			
			# Track number - title
			surface.blit(render_text(self.status["title"], self.font["details"]),
						pos("track", (0,self.draw_offset[1])))

			# Total time
			if self.status["timeElapsed"] and self.status["timeTotal"]:
				
				surface.blit(render_text(self.status["timeTotal"], self.font["elapsed"]),
							pos("track_length", (0,self.draw_offset[1])))
							
			# Draw player logo if it exists
			logo = self.playerlogos[self.pc.get_current()]
			if logo:
				surface.blit(self.image["background"], 
							pos("logoback",(0,self.draw_offset[1])), 
							(pos("logoback",(0,self.draw_offset[1])),
							size["logoback"]))
				surface.blit(logo, pos("logo",(0,self.draw_offset[1])))

			self.update_ack("trackinfo")
						
		# Time Elapsed
		if self.updated("elapsed") and self.pc("elapsed_enabled"):

			# Refresh backgrounds
			surface.blit(self.image["background"], 
						pos("progressbackground",(0,self.draw_offset[1])), 
						(pos("progressbackground",(0,self.draw_offset[1])), size["progressbackground"]))
			surface.blit(self.image["progress_bg"], 
		                 pos("progressbar", (0,self.draw_offset[1])))

			# Progress bar
			if self.seekpos == -1:
				progress = self.status["timeElapsedPercentage"]
			else: 
				progress = self.seekpos				
			surface.blit(self.image["progress_fg"], 
						pos("progressbar", (0,self.draw_offset[1])),
						(0,0,int(size["progressbar"][0]*progress),10))
			# Text
			surface.blit(render_text(self.status["timeElapsed"], self.font["elapsed"]),
						pos("elapsed", (0,self.draw_offset[1])))

			self.update_ack("elapsed")

		# Buttons
		if self.updated("repeat") and self.pc("repeat_enabled"):
			surface.blit(self.image["button_repeat"],
						pos("repeatbutton", (0,self.draw_offset[1])))
			self.update_ack("repeat")
			
		if self.updated("random") and self.pc("random_enabled"):
			surface.blit(self.image["button_random"],
						pos("randombutton", (0,self.draw_offset[1])))
			self.update_ack("random")
			
		#Volume
		if config.volume_enabled and self.updated("volume") and self.pc("volume_enabled"):
			surface.blit(self.image["volume_bg"],
						pos("volume", (0,self.draw_offset[1])))
			# Slider
			pos_volumefg = pos("volume_slider", (0,self.draw_offset[1]))
			if self.volumepos == -1:
				volumefg_scale = (self.status["volume"]*(size["volume_slider"][1])/100)
			else:
				volumefg_scale = (self.volumepos * (size["volume_slider"][1])/100)
			
			pos_volumefg = (pos_volumefg[0], pos_volumefg[1]+size["volume_slider"][1]-volumefg_scale)
			surface.blit(self.image["volume_fg"],
						(pos_volumefg))
			self.update_ack("volume")
	
		# Cover art
		if self.updated("coverart"):
			surface.blit(self.image["cover"],
						pos("coverart", self.draw_offset))
			surface.blit(self.image["coverart_border"], 
						pos("coverart", self.draw_offset))
			self.update_ack("coverart")
			
	def on_click_mainscreen(self, mousebutton, clickpos):

		allow_repeat = False
		
		# Coverart clicked - play/pause
		if clicked(clickpos, pos("coverart"), size["coverart"]):
			if mousebutton == 1:
				self.logger.debug("Toggle play/pause")
				self.pc.control_player("play_pause")

		# Repeat button
		if clicked(clickpos, pos("repeatbutton"), size["controlbutton"]) and self.pc("repeat_enabled"):
			self.pc.control_player("repeat")
		if clicked(clickpos, pos("randombutton"), size["controlbutton"]) and self.pc("random_enabled"):
			self.pc.control_player("random")

		# Volume 
		if config.volume_enabled and self.pc("volume_enabled") and clicked(clickpos, pos("volume_click"), size["volume_click"]):
			volume = (pos("volume_slider")[1]+size["volume_slider"][1]-clickpos[1])*100/size["volume_slider"][1]
			volume = limit(volume,0,100)
			self.pc.control_player("volume", volume)
		
		# Progress bar
		if self.pc("elapsed_enabled") and self.pc("seek_enabled"):		
			if clicked(clickpos, pos("progressbar"), size["progressbar_click"]) or clicked(clickpos, pos("elapsed"), size["elapsed"]):
				seek = float(clickpos[0]-pos("progressbar")[0])/float(size["progressbar"][0])
				seek = limit(seek,0.0,1.0)
				self.pc.control_player("seek", seek)
			
		# Return value: allow repeat
		return allow_repeat

	def scroll_mainscreen(self, start, x, y, end=False):

		# scrolling progress bar
		if self.pc("seek_enabled") and \
                  (clicked(start, pos("progressbar"), size["progressbar_click"]) or \
                   clicked(start, pos("elapsed"), size["elapsed"])) and \
                   abs(x) > 0:
			self.seekpos = float(start[0]+x-pos("progressbar")[0])/float(size["progressbar"][0])
			self.seekpos = limit(self.seekpos,0.0,1.0)
			if end:
				self.pc.control_player("seek", self.seekpos)
				self.seekpos = -1.0
				
		# scrolling volume
		elif config.volume_enabled and self.pc("volume_enabled") and \
		           clicked(start, pos("volume_click"), size["volume_click"]) and \
				   abs(y) > 0:
			self.volumepos = (pos("volume_slider")[1]+size["volume_slider"][1]-(start[1]+y))*100/size["volume_slider"][1]
			self.volumepos = limit(self.volumepos,0,100)
			if end:
				self.pc.control_player("volume", self.volumepos)
				self.volumepos = -1

		# Normal scroll
		else:
	
			# Scroll min/max limits
			x = 0 if abs(x) < 40 else x
			if y > 0:
				y = 0 if y < size["topmenu"] else y-y%size["topmenu"]
			else:
				y = 0 if abs(y) < size["bottommenu"] else y-y%size["bottommenu"]+size["bottommenu"]
			self.draw_offset = limit_offset((x,y),(-108, -len(self.pc.get_menu())*size["bottommenu"], 
			                                        108, (len(self.topmenu)-1)*size["topmenu"]))
	
			if x > 0:
				self.image["coverart_border"] = self.image["coverart_border_next"]
			elif x < 0:
				self.image["coverart_border"] = self.image["coverart_border_prev"]
			else:
				if self.pc["status"]["state"] == "play":
					self.image["coverart_border"] = self.image["coverart_border_clean"]
				else:
					self.image["coverart_border"] = self.image["coverart_border_paused"]
					
			if end:
				# Flip: next/prev
				if self.draw_offset[0] > 0:
					self.pc.control_player("next")
				elif self.draw_offset[0] < 0:
					self.pc.control_player("previous")
					
				# Top menu: Player selection
				for i in range (0,len(self.topmenu)-1):
					index = i if i < self.pc.get_current() else i+1

					if self.draw_offset[1] == (i+1)*size["topmenu"]:
						self.pc.control_player("switch", index)
										
				i = -self.draw_offset[1]//size["bottommenu"] - 1
				
				# Scroll limited to list length, but still check for fun
				if i > -1 and len(self.pc.get_menu()) >= i:
					menuitem = self.pc.get_menu()[i]
					self.switch_view("listview", menuitem)
						
				# Reset offset
				self.draw_offset = (0,0)
				# Reset cover image
				if self.pc["status"]["state"] == "play":
					self.image["coverart_border"] = self.image["coverart_border_clean"]
				else:
					self.image["coverart_border"] = self.image["coverart_border_paused"]		

	def render_listview(self,surface):
		list_draw_offset = self.list_offset%size['listitem_height']
		if self.listcontent:
			for i in range(-self.num_listitems,2*self.num_listitems):
				list_index = i+self.list_offset//size['listitem_height']
				list_length = len(self.listcontent)
				if list_index in range(0, list_length):
					try:
						# Parse information 
						# TODO: Do this more general
						if "title" in self.listcontent[list_index]:
							listitem = self.listcontent[list_index]["title"]
							if "artist" in self.listcontent[list_index]:
								listitem = self.listcontent[list_index]["artist"] + " - " + listitem
							if "pos" in self.listcontent[list_index]:
								position = int(self.listcontent[list_index]["pos"]) + 1
								position = str(position).rjust(4, ' ')
								listitem = position + ". " + listitem
								
						# No title, get filename
						elif "file" in self.listcontent[list_index]:
							listitem = self.listcontent[list_index]["file"].split("/")[-1]
							
						# PLaylists view
						elif "playlist" in self.listcontent[list_index]:
							listitem = self.listcontent[list_index]["playlist"]
						else: 
							listitem = self.listcontent[list_index]
						
					except Exception, e:
						listitem = ""
						self.logger.debug(e)
	
					text = render_text(listitem, self.font["details"], "text")
					# Highlight currently playing item
#					if self.listcontent[list_index].get("pos") == self.status["pos"]:
#						text = render_text(listitem, self.font["details"], "highlight")
					surface.blit(text, pos("listview", (self.draw_offset[0],self.draw_offset[1]-list_draw_offset+size['listitem_height']*i)))
		else: 
			self.switch_view("main")
			
	def on_click_listview(self, mousebutton, clickpos):
		if clicked(clickpos, pos("scrollbar"), size["scrollbar_click"]):
			ratio = float(clickpos[1])/float(config.resolution[1])
			self.list_offset = int(ratio*size["listitem_height"]*(len(self.listcontent)))
			self.list_offset = limit_offset((0,self.list_offset),(0, 0, 0, size["listitem_height"]*(len(self.listcontent)-self.num_listitems)))[1]

		# Normal click
		elif clicked(clickpos, (0,0), config.resolution):
			# Get index of item clicked
#				list_index = i+self.list_offset//size['listitem_height']
			click_index = (clickpos[1] + self.list_offset)//size["listitem_height"]
			if click_index > len(self.listcontent):
				click_index = len(self.listcontent)
			# Check return value: new list returned if something
			new_list = self.listclick(click_index, mousebutton)
			self.logger.debug(new_list)
			if not new_list:
				self.switch_view("main")
			else:
				self.switch_view("listview", new_list)
			
		# Return value: allow repeat
		return False

	def scroll_listview(self, start, x, y, end=False):
		# Prevent negative offset for short lists that fit on the screen
		if len(self.listcontent) > self.num_listitems:
			max_offset = size["listitem_height"]*(len(self.listcontent)-self.num_listitems)
		else:
			max_offset = 0

		# Scrollbar: fast scroll
		if clicked(start, pos("scrollbar"), size["scrollbar_click"]):
			ratio = float(start[1] + y)/float(config.resolution[1])
			self.list_offset = int(ratio*size["listitem_height"]*(len(self.listcontent)))
			self.list_offset = limit_offset((0,self.list_offset),(0, 0, 0, max_offset))[1]
			self.logger.debug("Scrollbar scroll")
			
		# Normal scroll
		else:
			self.draw_offset = limit_offset((x,y),(-config.resolution[0], -config.resolution[1], 
			                                        config.resolution[0],  config.resolution[1]))
		if end:
			self.list_offset = self.list_offset - self.draw_offset[1]
			self.list_offset = limit_offset((0,self.list_offset),(0, 0, 0, max_offset))[1]
			self.draw_offset = (0,0)

			# Horizontal scroll exits
			if abs(x) > 30:
					self.switch_view("main")

	def update_ack(self, updated):
		self.status["update"][updated] = False
		
	def updated(self, item):
		return self.status["update"][item]
		
	def force_update (self,item="all"):
		if item == "all":
			self.status["update"] = dict.fromkeys(self.status["update"], True)
		else:
			self.status["update"][item] = True

	def get_backlight_status(self):
		return self.backlight

	def toggle_backlight(self):
		if self.backlight:
			self.turn_backlight_off()
		else:
			self.turn_backlight_on()

	def turn_backlight_off(self,forced=False):
		self.logger.debug("Backlight off")
		subprocess.call("echo '0' > /sys/class/gpio/gpio508/value", shell=True)
		self.backlight = False
		self.backlight_forced_off = forced


	def turn_backlight_on(self):
		self.logger.debug("Backlight on")
		subprocess.call("echo '1' > /sys/class/gpio/gpio508/value", shell=True)
		self.backlight = True
		self.backlight_forced_off = False

		# Update screen timeout timer
		if config.screen_timeout > 0:
			self.update_screen_timeout()

	def update_screen_timeout(self):
		if self.get_backlight_status():
			self.screen_timeout_time = datetime.datetime.now() + timedelta(seconds=config.screen_timeout)
		else:
			self.turn_backlight_on()