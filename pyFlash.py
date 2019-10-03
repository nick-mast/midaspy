#Commands to flash detectors by issuing odbedit commands
#This is based on some commands in the flashandflash.py code which creates MIDAS Sequencer scripts to do the same thing

#NM 7/2019

import os
import pyodbedit as poe

def turnQBiasOff(pdcrc):
	#loop over the DCRC list and turn off Qbias
	for board in pdcrc:
		pyodbedit.write('/Equipment/Tower01/Settings/DCRC'+str(board)+'/Charge/Bias (V)[0]','0')
		pyodbedit.write('/Equipment/Tower01/Settings/DCRC'+str(board)+'/Charge/Bias (V)[1]','0')
	
	return 

def get15VPowerEnable(pdcrc):
	#loop over the DCRC list and save 15V power states
	state=[]
	for board in pdcrc:
		state.append(pyodbedit.read('/Equipment/Tower01/Settings/DCRC'+str(board)+'/LED/Enable15VPower'))
	
	return state 

def set15VPowerEnable(pdcrc, dcrcSettings):
	#loop over the DCRC and settings lists and set appropriate settings
	for board,setting in zip(pdcrc,dcrcSettings):
		pyodbedit.write('/Equipment/Tower01/Settings/DCRC'+str(board)+'/LED/Enable15VPower',str(setting))
	
	return 

def turn15VPowerEnableOn(pdcrc):
	#loop over the DCRC list and enable 15V power
	for board in pdcrc:
		pyodbedit.write('/Equipment/Tower01/Settings/DCRC'+str(board)+'/LED/Enable15VPower','y')
	
	return 

def setUpLEDs(pdcrc,pcur,pwidth,prep):
	#set durations and stuff
	pyodbedit.write('/Equipment/Tower01/Settings/DCRC'+str(pdcrc)+'/LED/LEDPulseWidth (us)',str(pwidth))
	pyodbedit.write('/Equipment/Tower01/Settings/DCRC'+str(pdcrc)+'/LED/LEDRepRate (us)',str(prep))
	pyodbedit.write('/Equipment/Tower01/Settings/DCRC'+str(pdcrc)+'/LED/LED1Current (mA)',str(pcur))
	pyodbedit.write('/Equipment/Tower01/Settings/DCRC'+str(pdcrc)+'/LED/LED2Current (mA)',str(pcur))
	
	return 

def enableLEDs(pdcrc,onoff):
	if(onoff==0):
		state='n'
	else:
		state='y'

	for board in pdcrc:
		pyodbedit.write('/Equipment/Tower01/Settings/DCRC'+str(board)+'/LED/EnableLED1',state)
		pyodbedit.write('/Equipment/Tower01/Settings/DCRC'+str(board)+'/LED/EnableLED2',state)
	
	return 
