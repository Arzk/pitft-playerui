import config
from positioning import pos, size, color, _pos, _render_text, _clicked, _get_scroll_rect, _limit_offset

class Mainscreen:
	def __init__(self, font):
	
		self.logger = logging.getLogger("PiTFT-Playerui.Screen_Manager.Mainscreen")
		self.font = font
		self.offset = (0,0)

	def render(self, surface, offset, image, status):
		self.offset = _limit_offset(self.offset,(108,40))

		# Menu texts on top and bottom
		if updated("screen"):
			surface.blit(_render_text("PLAYLIST", self.font["details"], "text"),
                         _pos("PLAYLIST", self.offset)) # Title"
			surface.blit(_render_text("MENU", self.font["details"], "text"),
                         _pos("MENU", self.offset)) # Title

		# Cover art
		if updated("coverart") or updated("screen"):
			self.logger.debug("Updating coverart")
			surface.blit(self.image["cover"],_pos("coverart", self.offset))
			surface.blit(self.image["coverart_border"], _pos("coverart", self.offset))
			self.update_ack("coverart")
			self.update_ack("screen")
			
	def on_click(self, mousebutton, click_pos):
	
		# Coverart clicked - play/pause
		if _clicked(click_pos, pos["coverart"], size["coverart"]):
			if mousebutton == 1:
				self.logger.debug("Toggle play/pause")
				self.pc.control_player("play_pause")
				return False
			# DEBUG: Switching player on button 2 for now
			elif mousebutton == 2:
				self.logger.debug("Switching player")
				self.pc.switch_active_player()
				return False
					
		# Return value: allow repeat
		return False
		
	def scroll(self, x, y, end=False):
		if end:
			if x > 60:
				self.pc.control_player("next")
			elif x < -60:
				self.pc.control_player("previous")
				
			if y < -30:
				self.switch_screen("playlist")