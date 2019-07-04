# -*- coding: utf-8 -*-
import logging

class PlayerBase(object):
    def __init__(self, name, config):
        self.logger = logging.getLogger("PiTFT-Playerui." + name)
        self.coverartThread = None
        self.config = config

        # Capabilities
        self.capabilities = {
            "name"            : name,
            "connected"       : False,
            "volume_enabled"  : False,
            "seek_enabled"    : False,
            "random_enabled"  : False,
            "repeat_enabled"  : False,
            "elapsed_enabled" : False,
            "logopath"        : "",
            "logo"            : None
        }
        # Things to remember
        self.data = {
            "status" : {},
            "song"   : {},
            "cover"  : False,
            "coverartfile" : "",
            "update" : {},
            "list" :
            {
                "type"        : "",
                "content"     : [],
                "viewcontent" : [],
                "click"       : self.list_click,
                "highlight"   : -1,
                "position"    :  0,
                "buttons"     : []
            },
            "menu" : []
        }
        self.init_data()
        
    def init_data (self):
        self.data["status"] = {
                "state"       : "",
                "elapsed"     : "",
                "repeat"      : "",
                "random"      : "",
                "volume"      : "",
                "playlistlength" : 0
            }            
        self.data["song"] = {
                "pos"         : "",
                "artist"      : "",
                "album"       : "",
                "date"        : "",
                "track"       : "",
                "title"       : "",
                "time"        : "",
                "cover_uri"   : ""
            }
        self.data["cover"] = False
        self.data["coverartfile"] = ""
        self.data["update"] = {
                "active"      : False,
                "state"       : True,
                "elapsed"     : True,
                "random"      : True,
                "repeat"      : True,
                "volume"      : True,
                "trackinfo"   : True,
                "coverart"    : True
            }
            
    """ Get data """
    def __getitem__(self, item):
        return self.data[item]

    """ Get capability value """
    def __call__(self, item):
        return self.capabilities[item]

    def set_logo(self, item):
        self.capabilities["logo"] = item

    """ Refresh data from API """
    def refresh(self, active=False):
        pass

    """ Force an update """
    def force_update (self,item="all"):
        if item == "all":
            self.data["update"] = dict.fromkeys(self.data["update"], True)
        else:
            self.data["update"][item] = True

    """ Acknowledge an update request """
    def update_ack(self, updated):
        self.data["update"][updated] = False

    """ Control the player via API """
    def control(self, command, parameter=-1):
        pass

    """ Return value: Request next view ("listview", "contextmenu", None) """
    def list_click(self, item=-1, button=1):
        return None
