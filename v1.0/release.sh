#!/bin/bash
#
# script to copy lastest dev version to release directory where auto execution will commence
#
# baloothebear   7/1/18
# v0.1
#
echo "releasing PreDAC application"
cp display.py ~/share/preDACrel
cp fonts/* ~/share/preDACrel/fonts
cp hwinterface.py ~/share/preDACrel
cp icons/* ~/share/preDACrel/icons
cp octave.py ~/share/preDACrel
cp rotary_class.py ~/share/preDACrel
cp screenobjs.py ~/share/preDACrel
cp volumeboard.py ~/share/preDACrel
echo "all done"
