#!/usr/bin/env python3
# Python frontend for playing SomaFM with MPlayer
# Licensed under the GPLv3, see "COPYING"
version = "1.0"

import re
import os
import sys
import pickle
import shutil
import signal
import requests
import argparse
import datetime
import colorama
import subprocess
from colorama import Fore, Style
from collections import OrderedDict

# Default quality (0 is highest available)
quality_num = 0

# Default channel to play
default_chan = "Groove Salad"

# SomaFM channel list
url = "https://somafm.com/channels.json"

# File to keep local copy
channel_file = "/tmp/soma_channels"

# Define functions
#-----------------------------------------------------------------------#
# Catch ctrl-c
def signal_handler(sig, frame):
    print(Fore.RED + "Force closing...")
    # Try this
    playstream.terminate()
    # But also this
    os.system('killall mplayer')
    sys.exit(0)

# Download master list of channels
def downloadChannels():
    # Make global so other functions can acess it
    global channel_list

    # Let user know we're downloading
    print("Downloading channel list...", end='')
    sys.stdout.flush()

    # Pull down JSON file
    try:
        channel_raw = requests.get(url, timeout=15)
    except requests.exceptions.Timeout:
        print("Timeout!")
        exit()
    except requests.exceptions.ConnectionError:
        print("Network Error!")
        exit()
    except requests.exceptions.RequestException as e:
        print("Unknown Error!")
        exit()

    # Put channels in list
    channel_list = channel_raw.json()['channels']

    # Write to file
    with open(channel_file, 'wb') as fp:
        pickle.dump(channel_list, fp)

    print("OK")

# Loop through channels and print their descriptions
def listChannels():
    # Loop through channels
    print(Fore.RED + "------------------------------")
    for channel in channel_list:
        print(Fore.BLUE + '{:>22}'.format(channel['title']) + Fore.WHITE, end=' : ')
        print(Fore.GREEN + channel['description'] + Fore.RESET)

# Show sorted list of listeners
def showStats():
    # To count total listeners
    listeners = 0

    # Dictionary for sorting
    channel_dict = {}

    # Put channels and listener counts into dictionary
    for channel in channel_list:
        channel_dict[channel['title']] = int(channel['listeners'])

    # Sort and print results
    sorted_list = OrderedDict(sorted(channel_dict.items(), key=lambda x: x[1], reverse=True))
    print(Fore.RED + "------------------------------")
    for key, val in sorted_list.items():
        # Total up listeners
        listeners = listeners + val
        print(Fore.GREEN + '{:>4}'.format(val) + Fore.BLUE, end=' : ')
        print(Fore.BLUE + key + Fore.RESET)

    # Print total line
    print(Fore.YELLOW + '{:>4}'.format(listeners) + Fore.BLUE, end=' : ')
    print(Fore.CYAN + "Total Listeners" + Fore.RESET)

# Return playlist URL for given channel name
def getPLS(channel_name):
    for channel in channel_list:
        if channel_name == channel['title']:
            return(channel['playlists'][quality_num]['url'])

    # If we get here, no match
    print(Fore.RED + "Channel not found!")
    print(Fore.WHITE + "Double check the name of the channel and try again.")
    print("Channel names must be entered EXACTLY as they are seen in the list.")
    exit()

# Execution below this line
#-----------------------------------------------------------------------#
# Load signal handler
signal.signal(signal.SIGINT, signal_handler)

# Handle arguments
parser = argparse.ArgumentParser(description='Simple Python 3 player for SomaFM, version ' + version)
parser.add_argument('-l', '--list', action='store_true', help='Download and display list of channels')
parser.add_argument('-s', '--stats', action='store_true', help='Display current listener stats')
parser.add_argument("channel", nargs='?', const=1, default=default_chan, help="Channel to stream. Default is Groove Salad")
args = parser.parse_args()

# Get screen ready
colorama.init()
os.system('clear')
print(Style.BRIGHT, end='')

if args.list:
    # Always download, this allows manual update
    downloadChannels()
    listChannels()
    exit()

if args.stats:
    downloadChannels()
    showStats()
    exit()

# If we get here, we are playing
# Check for MPlayer before we get too comfortable
if shutil.which("mplayer") == None:
    print(Fore.RED + "MPlayer not found!")
    print(Fore.WHITE + "MPlayer is required for this script to function.")
    exit()

if os.path.isfile(channel_file) == False:
    downloadChannels()

# Load local channel list
with open (channel_file, 'rb') as fp:
    channel_list = pickle.load(fp)

# Find playlist for given channel
stream_url = getPLS(args.channel)

# Open stream
print("Loading stream...", end='')
playstream = subprocess.Popen(['mplayer', '-playlist', stream_url], stdout=subprocess.PIPE, stderr=subprocess.STDOUT, shell=False)
print("OK")
print(Fore.RED + "--------------------------")
print(Fore.WHITE, end='')
# Parse output
for line in playstream.stdout:
    if line.startswith(b'Name'):
        print(Fore.CYAN + "Channel: " + Fore.WHITE + line.decode().split(':', 2)[1].strip())
    if line.startswith(b'Genre'):
        print(Fore.CYAN + "Genre: " + Fore.WHITE + line.decode().split(':', 1)[1].strip())
    if line.startswith(b'Bitrate'):
        print(Fore.CYAN + "Bitrate: " + Fore.WHITE + line.decode().split(':', 1)[1].strip())
        print(Fore.RED + "--------------------------")
    if line.startswith(b'ICY Info:'):
        info = line.decode().split(':', 1)[1].strip()
        attrs = dict(re.findall("(\w+)='([^']*)'", info))
        print(Fore.BLUE + datetime.datetime.now().strftime("%H:%M:%S"), end=' | ')
        print(Fore.GREEN + attrs.get('StreamTitle', '(none)'))

print(Fore.RESET + "Playback stopped.")
# EOF
