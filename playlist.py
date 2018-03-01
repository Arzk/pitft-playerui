from positioning import pos, size, color, _pos, _render_text, _clicked, _get_scroll_rect, _limit_offset

class playlist(font, image):
	def __init__(self):
		self.logger = logging.getLogger("PiTFT-Playerui.Screen_Manager.Playlist")
		self.font = font
		self.image = image


	def render(self,surface,offset):
		self.offset = _limit_offset(self.offset)
		self.screen="playlist"
		try:
			surface.blit(_render_text("MAIN", self.font["details"], "text"),
						_pos("MAIN", (self.offset[0],0))) # Title
		except Exception, e:
			self.logger.exception(e)
	
		surface.blit(_render_text("testingtestingtestingtestingtestingtesting", self.font["details"], "text"),
						_pos("playlist", (self.offset[0],0))) # Title
		
	def on_click(self, mousebutton, click_pos):
		if _clicked(click_pos, (0,0), config.resolution):
			return False
					
		# Return value: allow repeat
		return False
	
	def scroll(self, x, y, end=False):
		if end:
			if abs(x) > 30:
				self.switch_screen("main")
	