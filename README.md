# preDAC - HiFi preamplifier control and visualisation

Control and audio processing of an integrated preamplifier, with a range of visualisation screen eg VU meters and Spectrum Analysers.  Plus this has remote controlled volume control (of a ladder volume control) and control source.

## Installation
1.  Create a new SD card based off a build of [Moode]([url](https://moodeaudio.org)https://moodeaudio.org) - this creates a base audio player
2.  Update the Pi libraries and packages
```
sudo apt update
sudo apt upgrade
sudo apt install git
```
3. Copy down all of the application code
```
git clone ...
``` 
4.  Install all the dependent packages
```  
cd preDAC
sudo pip3 install requirements.txt 
```
5. Move the config files to the correct locations
```
config.txt
.lirc
preDAC.service
``` 
6. Start the autorunning service
```
sudo systemcmd preDAC.service
reboot
``` 
7. All good to listen to great music


