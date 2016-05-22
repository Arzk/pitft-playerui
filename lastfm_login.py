# -*- coding: utf-8 -*-
import pylast

# You have to have your own unique two values for API_KEY and API_SECRET
# Obtain yours from http://www.last.fm/api/account for Last.fm
API_KEY = "API_KEY"
API_SECRET = "API_SECRET"

# In order to perform a write operation you need to authenticate yourself
username = "USERNAME"
password_hash = pylast.md5("PASSWORD")
