#!/etc/sh
echo "mVista PreDAC build environment file"

#create build environment

sudo apt update
sudo apt upgrade


Echo "copy base files into preDACdev directory from GitHub"

# Git file download
sudo apt-get install git
echo "git files not installed -> copy manually"

sudo apt-get install netatalk



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
