# -*- coding: utf-8 -*-
import logging
import config
from spotify_control import SpotifyControl
from mpd_control import MPDControl
from cd_control import CDControl

class PlayerControl:
    def __init__(self):
        self.logger  = logging.getLogger("PiTFT-Playerui.Player_Control")
        self.players = []
        self.current = 0

        try:
            self.logger.debug("Setting Spotify")
            if config.spotify_host and config.spotify_port:
                self.players.append(SpotifyControl())
        except Exception, e:
            self.logger.debug(e)
        try:
            self.logger.debug("Setting MPD")
            if config.mpd_host and config.mpd_port:
                self.players.append(MPDControl(config))
        except Exception, e:
            self.logger.debug(e)
        try:
            self.logger.debug("Setting CD")
            if config.cdda_enabled:
                self.players.append(CDControl())
        except Exception, e:
            self.logger.debug(e)

        # Quit if no players
        if not len(self.players):
            self.logger.debug("No players defined! Quitting")
            raise

        self.logger.debug("Player control set")

    def __getitem__(self, item):
        if self.players[self.current]:
            return self.players[self.current][item]
        else:
            return {}

    def __call__(self, item):
        return self.players[self.current](item)

    def get_players(self):
        playerlist = []
        for player in self.players:
            if player("connected"):
                playerlist.append({'name': player("name").upper(), 'logopath': player("logopath")})
        return playerlist

    def get_current(self):
        return self.current

    def determine_active_player(self):
        active = -1
        # Find changes in activity
        for id, player in enumerate(self.players):
            if player["update"]["active"]:
                active = id
                self.logger.debug("Player %s started: %s" % (id, player("name")))
                self.switch_active_player(id)

        # Player started: pause the rest
        if active != -1:
            for id, player in enumerate(self.players):
                if id != active:
                    if player["status"]["state"] == "play":
                        self.logger.debug("pausing %s" % player("name"))
                        self.control_player("pause", 0, id)


    # force (bool): update all players
    def refresh(self, force=False):
        # Update all for active, only status for rest
        for id, player in enumerate(self.players):
            try:
                player.refresh(self.current == id or force)
            except Exception, e:
                self.logger.debug(e)

        # Get active player
        self.determine_active_player()

    def update_ack(self, updated):
        self.players[self.current].update_ack(updated)

    def control_player(self, command, parameter=0, id=-1):
        # Translate
        if self.players[self.current]["status"]:
            if command == "play_pause":
                if self.players[self.current]["status"]["state"] == "play":
                    command = "pause"
                else:
                    command = "play"

        # Switching commands
        if command == "radio":
            self.load_playlist(config.radio_playlist)
        elif command == "switch":
            self.switch_active_player(parameter)

        # Player specific commands
        elif id != -1:
            self.players[id].control(command, parameter)
        # ID not specified
        else:
            self.players[self.current].control(command, parameter)

    def switch_active_player(self, id):
        player_changed = False
        if self.current != id:
            player_changed = True
            self.current = id
            self.logger.debug("Switching player to %s" % self.players[id]("name"))

        # Player changed, refresh data
        if player_changed:
            self.players[self.current].force_update()
        # Ack the request
        self.players[self.current].update_ack("active")

    def get_active_player(self):
        return self.current