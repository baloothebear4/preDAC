#!/etc/sh
#
# preDAC project
# baloothebear4  v2.0 26 May 2020 - upgrade to new HW
#

echo "PreDAC build environment file"

#create build environment

sudo apt update
sudo apt upgrade


Echo "copy base files into preDACdev directory from GitHub"

# Git file download
sudo apt-get install git
cd ~
git clone https://github.com/baloothebear4/preDAC.git

Echo "setup Python packages"
sudo apt-get install python3-dev python3-setuptools
sudo pip3 pcf8574 pillow numpy luma.core
sudo apt-get install libportaudio0 libportaudio2 libportaudiocpp0 portaudio19-dev
sudo pip3 install pyalsaaudio

#Samba Setup
#Edit the /etc/samba/smb.conf file and add the following lines. These lines #define the behaviour of the shared folder so you can call them share #definition.
#[pishare]
#    comment = Pi Shared Folder
#    path = /home/pi/shared
#    browsable = yes
#    guest ok = yes
#    writable = yes

Echo "Make sure the smb.conf file is copied to
sudo apt-get install samba
mkdir /home/pi/shared
chmod 777 /home/pi/shared
sudo /etc/init.d/samba restart
