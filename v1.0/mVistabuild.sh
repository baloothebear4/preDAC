#!/bin/sh
echo "mVista build environment file"

#create build environment

sudo apt update
sudo apt upgrade


Echo "copy base files into preDACdev directory from GitHub"

# Git file download
sudo apt-get install git
echo "git files not installed -> copy manually"


sudo pip install python-mpd2
sudo apt-get install python-tk       #neededfor cover art resizing

sudo git clone https://github.com/luckydonald/shairport-decoder
cd shairport-decoder
sudo python setup.py install

sudo pip install mutagen    # for ID tag interrogation
