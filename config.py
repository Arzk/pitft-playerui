###############
# Settings
###############

# Log level, valid values INFO and DEBUG
loglevel = "INFO"

# time in seconds before the screen turns off if not playing
# 0: disabled
screen_timeout = 0

###############
# MPD
###############

# Path to MPD
mpd_host = "localhost"
mpd_port = "6600"

# Music library location as set in MPD
# Leave empty to disable local coverart fetching
library_path = ""

# Enable volume control. True/False
volume_enabled = False

# Radio playlist name in MPD
# This playlist is toggled by a specific button and hidden from the playlists
# Leave empty to disable the button

radio_playlist = "Radio"

# Enable audio CD support via cdio_paranoia plugin and cddb-py. True/False
cdda_enabled = False

###############
# Spotify
###############

# Path to spotify-connect-web
# Leave empty to disable
spotify_host = "localhost"
spotify_port = "4000"

###############
# Last.FM
###############

# You have to have your own unique two values for API_KEY and API_SECRET
# Obtain yours from http://www.last.fm/api/account for Last.fm
API_KEY = ""
API_SECRET = ""

# In order to perform a write operation you need to authenticate yourself
username = ""
password_hash = ""
