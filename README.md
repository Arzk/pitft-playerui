PiTFT-PlayerUI is a fork of PMB-PiTFT (Pi MusicBox PiTFT) that is a small Python script that uses mopidy's mpd-api to show controlling ui on Raspberry Pi's screen.

![Screenshot](https://dl.dropboxusercontent.com/u/15996443/github/pitft-playerui.png)

Forking reasons:
===========
- Support for 3.5" PiTFT+
- Audio CD tag fetching from FreeDB
- Spotify-connect-web support (https://github.com/Fornoth/spotify-connect-web)
- Alternative UI with cleanup (sleep time and volume control disabled) 
- My first python project
 
Features:
===========
Shows following details of currently playing track:
- Cover art (From Last.FM)
- Artist, Album and Track title
- Track time total and elapsed
- Fetches audio CD information from freeDB

Shows and lets user control:
- Repeat
- Random
- Playback status
- Playlists
- CD playback
- Radio playback

Lets user control:
- Screen backlight

Things you need:
=================
- Raspberry pi (I am using model 3B)
- Adafruit PiTFT+ 3.5" with Resistive Touchscreen ( https://www.adafruit.com/product/2441 )
- Internet connection for Pi
- Raspbian running on the Pi
- MPD configured
- [Optional] Helvetica Neue Bold-font. You can use normal Helvetica Bold as well or some other font.

Known issues:
==============
- Long playlist items overlap buttons
- Doesn't check if a CD drive is connected

Installing:
===========
Current installation guide is tested and working with: Resistive PiTFT+ 3.5" + Raspberry Pi 3 Raspbian Jessie.

Install Raspbian and MPD and Configure PiTFT+ using the guide by Adafruit: https://learn.adafruit.com/adafruit-pitft-3-dot-5-touch-screen-for-raspberry-pi/ 
Detailed install and calibration recommended

Install dependencies:
<pre>apt-get update
apt-get install python-pygame
pip install python-mpd2
apt-get install evtest tslib libts-bin</pre>

For CD support also install cddb-py module:
http://cddb-py.sourceforge.net/

Download PiTFT-playerui files from github.
To be sure to start in the home directory do

<code>cd ~</code>

Then install git:

<code>apt-get install git-core</code>

After installing clone the git repository:

<code>git clone https://github.com/Arzk/pitft-playerui.git</code>

From pitft-ui.py you need to change the font if you are using something else than Helvetica Neue Bold and check that path is correct.

To change the font edit /root/pitft-playerui/pitft-playerui/pitft_ui.py file line 29 and replace "helvetica-neue-bold.ttf" with your own font name. example "OpenSans-Bold.ttf". You can download Open Sans from www.fontsquirrel.com/fonts/open-sans. Transfer ttf file to /home/pi/pitft-playerui/ folder.

You also have to set the LastFM api key and login information in lastfm_login.py file.

Create the log folder in /var/log/pitft-playerui:
<pre>sudo mkdir /var/log/pitft-playerui
sudo chown pi:pi /var/log/pitft-playerui # If not run by root</pre>

For display backlight control write these lines to /etc/rc.local:
<pre>echo 508 > /sys/class/gpio/export
echo 'out' > /sys/class/gpio/gpio508/direction</pre>

This is now daemon and it has three commands: start, restart and stop.

Use the following command to start ui:

<code>sudo python /home/pi/pitft-playerui/pitft-playerui/ui.py start</code>

To run the script as a service, copy the systemd service file to /etc/systemd/system:
<code>sudo cp systemd/pitft-playerui.service /etc/systemd/system/</code>

Note that using the framebuffer requires root access. The script can also be run in X window, for example via X forwarding in PuTTY, without sudo.

Some specific things:
=========
- The radio UI button expects to find a playlist named "Radio". The Radio playlist is hidden from the playlists view
- The active player view is decided between MPD and Spotify so that:
	- MPD is always shown on start
	- If Spotify is playing and MPD starts playing, pause Spotify and switch to MPD
	- And vice versa if Spotify starts playing

TODO:
=========
- Gestures
- Scrollable lists
- Sleep timer
- Cover art from Spotify
- Got other ideas? Post an issue and tell me about it

Author notes:
=============

There might be some bugs left. Feel free to give any improvement ideas.

Thanks:
===========
<pre>ISO-B
For the pmb-pitft
https://github.com/ISO-B/pmb-pitft</pre>

<pre>Ben Gertzfield
For the CDDB module
http://cddb-py.sourceforge.net/</pre>

<pre>Pi MusicBox Team
For making this great audio system
http://www.pimusicbox.com/</pre>

<pre>Notro and other people on project FBTFT
For making drivers for screen
https://github.com/notro/fbtft/wiki</pre>

<pre>project pylast @ github
For their Last.FM Python library
https://github.com/pylast/pylast</pre>

<pre>project python-mpd2 @ github
For their MPD-client Python library
https://github.com/Mic92/python-mpd2</pre>

<pre>Matt Gentile @ Icon Deposit
For his awesome Black UI Kit
http://www.icondeposit.com/design:108</pre>

<pre>Biga
Petite Icons
http://www.designfreebies.com/2011/10/20/petite-icons/</pre>
