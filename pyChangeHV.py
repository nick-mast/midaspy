# Issues a set of odbedit commands to change the HV bias
# This is an alternative to changeHV.py which creates MIDAS sequencer scripts
# The HV bias is controlled by a circuit which uses a DCRC's Qi bias to scale
# the power supply voltage
#
#Nick Mast 7/2019
#

import sys
import time
import argparse
from argparse import ArgumentParser, ArgumentTypeError

import flashandflash
import pyodbedit

#Ramp the HV settings appropriately
#Uses "calcBiasSetting", so heed all warnings therin
#iDCRC = MIDAS DCRC number
def changeHVFromTo(iDCRC,HVstart,HVend,HVrampRate,HVrampUpdatePeriod,calTable):
	HVcurr=HVstart
	HVincrement=HVrampRate*float(HVrampUpdatePeriod)
	#Increase HV by [HVincrement] every [HVrampUpdatePeriod] seconds
	while HVcurr!=HVend:
		if (abs(HVend-HVcurr) < HVincrement):
			HVcurr=HVend
		else:
			sign=(1.0*(HVcurr<HVend)-0.5)/0.5
			HVcurr=HVcurr+sign*HVincrement

		setting=calcBiasSetting(HVcurr,calTable)
		if setting==None:
			#Something went wrong
			sys.exit("****Bad bias setting****")
		setDCRCQI(iDCRC,round(setting,3))
		time.sleep(HVrampUpdatePeriod)
	return

#Calculate the DCRCQI setting needed for a given HV bias
#Interpolate based on calibration table
def calcBiasSetting(HV,calTable):
	#Assume cal table has DCRC setting as first entry and HV value as second
	#Also assume the list is ordered
	setA=calTable[0][0]
	HVA=calTable[0][1]
	if(HVA==HV):
		#We've found the entry exactly
		return setA
	
	for entry in calTable:
		setB=entry[0]
		HVB=entry[1]
		if (HVB==HV):
			#We've found the entry exactly
			return setB
		elif (HVA<HV and HV<HVB) or (HVA>HV and HV>HVB):
			#We've found the surrounding entries
			m=(setB-setA)/(HVB-HVA)
			setting = setA + m*(HV-HVA)
			return setting
		setA=setB
		HVA=HVB
	
	#If we make it here, the requested HV was outside the calibration region.
	return None

#Set DCRCQI bias
def setDCRCQI(iDCRC,V):	
	pyodbedit.write('/Equipment/Tower01/Settings/DCRC'+str(iDCRC)+'/Charge/Bias (V)[0]',str(V))
	return

#Turn the HV power supply on or off
#state=1 is on, state=0 is off
def setHVpowerOnOff(iDCRC,state):
	if state==1 or str(state).lower()=='on':
		print 'Turn HV power supply ON'
		pyodbedit.write('/Equipment/Tower01/Settings/DCRC'+str(iDCRC)+'/Charge/Bias (V)[1]', str(10))
		time.sleep(5)
	elif state==0 or str(state).lower()=='off':
		print 'Turn HV power supply OFF'
		pyodbedit.write('/Equipment/Tower01/Settings/DCRC'+str(iDCRC)+'/Charge/Bias (V)[1]', str(0))
		time.sleep(5)
	else:
		#Something went wrong
		sys.exit("****Bad power supply state setting****")
	return

#Load the HV setting calibration table
#Assume the first row is a header
def loadCalTable(HVcalFile):
	cals=[]
	with open(HVcalFile,'r') as f:
		header=next(f)
		for line in f:
			entries=line.strip().split('\t')
			#First entry is DCRC setting, second is HV
			cals.append([float(entries[0]),float(entries[1])])
	return cals




#This is the real main
#To call this from another script, you pass the same args you would from the command line, but as a list of strings
# e.g. changeHV.main(["-HVstart","0","-HVend","45","-HVcalFile","/some/file/path.txt"])
########################################################################
def main(args):

	###############################################
	#Set up command line inputs and options
	###############################################
	parser = argparse.ArgumentParser(description='Get run info')
	
	parser.add_argument('-iDCRC',type=int,help='MIDAS DCRC number of board controlling HV')
	parser.add_argument('-HVstart',type=str,help='Current HV setting')
	parser.add_argument('-HVend',type=str,help='Desired HV setting')

	parser.add_argument('-HVcalFile',type=str,help='Calibration file. Should be a tab-separated file with the first column being the DCRCQI control voltage and the second being the resulting HV output voltage. These values should be in numerical order. The first row is reserved for column headers. Note: This code is very stupid, so make sure the format is correct!')

	parser.add_argument('-HVrampRate',type=float,default=1.0,help='Rate limit for HV voltage changes in V/s (default is 1 V/s)')
	parser.add_argument('-HVrampUpdatePeriod',type=int,default=1,help='Period of time (in s) to wait between HV voltage changes while ramping. Default is 1 s.')
	parser.add_argument('-HVpreBias',type=str,help='Prebias settings for HV. Should be in the form (Overbias %%)/(wait time min). As in 15/5 to overbias by 15%% for 5 minutes. No prebias by default')

	args = parser.parse_args(args)

	###########################
	#Parse command line inputs
	###########################
#TODO: catch missing/incorrectly formatted arguments
	if (args.iDCRC is None) or (args.HVstart is None) or (args.HVend is None) or (args.HVcalFile is None):
		parser.error('Error: missing required input. See changeHV -h for info.')

	iDCRC=int(args.iDCRC)
	HVstart=float(args.HVstart)
	HVend=float(args.HVend)
	HVcalFile=args.HVcalFile

	HVrampRate=args.HVrampRate
	
	if args.HVrampUpdatePeriod<1.0:
		parser.error('Minimum HVrampUpdatePeriod is 1 s')
	else:
		HVrampUpdatePeriod=args.HVrampUpdatePeriod
	
	if not (args.HVpreBias is None):
		HVpreBiasPercent=float(args.HVpreBias.split('/')[0])
		HVpreBiasWait_sec=int(60.0*float(args.HVpreBias.split('/')[1]))

	###########################
	#Load calibration lookup table
	###########################
	cals=loadCalTable(HVcalFile)

	###########################
	#Output Sequence
	###########################
	print 'Change HV bias from ' + str(HVstart) + ' V to ' + str(HVend) +' V using DCRC'+str(iDCRC)
	print
	###########
	#Set HV
	###########
	if args.HVpreBias is None:
		#Just ramp to new HV
		print 'Set HV = '+str(HVend)
		changeHVFromTo(iDCRC,HVstart,HVend,HVrampRate,HVrampUpdatePeriod,cals)
	else:
		print 'Prebias by ' + str(HVpreBiasPercent) + '% for ' + str(HVpreBiasWait_sec/60.) + ' minutes'
		#Ramp to prebias
		HVpre=round((1.0+HVpreBiasPercent/100.)*HVend,2)
		print 'Set HVpre = '+str(HVpre)
		changeHVFromTo(iDCRC,HVstart,HVpre,HVrampRate,HVrampUpdatePeriod,cals)
		#Wait
		print 'Waiting '+str(HVpreBiasWait_sec)+' sec'
		time.sleep(HVpreBiasWait_sec)
		#Ramp down to desired HV
		print 'Set HV = '+str(HVend)
		changeHVFromTo(iDCRC,HVpre,HVend,HVrampRate,HVrampUpdatePeriod,cals)

	print


#This is a work around so this can be called from the command line or another script
########################################################################
if __name__ == "__main__":
	main(sys.argv[1:])

