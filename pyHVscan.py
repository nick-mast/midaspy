# Program to issue odbedit commands to manipulate MIDAS to take HV scan data without using the Sequencer
# The HV bias is controlled by a circuit which uses a DCRC's QI bias to scale
# the power supply voltage
# This is an alternateive to MIDAS Sequence generating scripts such as HVscan.py
#
#Nick Mast 7/2019
#
import sys
import argparse
from argparse import ArgumentParser, ArgumentTypeError

import pyChangeHV
import pyodbedit
import pyflash

#the stuff below is so this functionality can be used as a script
########################################################################
if __name__ == "__main__":

	###############################################
	#Set up command line inputs and options
	###############################################
	parser = argparse.ArgumentParser(description='Get run info')

	#DCRC number	
	parser.add_argument('-iDCRC',type=int,help='MIDAS DCRC number of board controlling HV')
	#Voltage Biases
	parser.add_argument('-HVs',type=str,help='Comma-separated list of bias voltages in desired run order.')
	parser.add_argument('-HVcalFile',type=str,help='Calibration file. Should be a tab-separated file with the first column being the DCRC4QI control voltage and the second being the resulting HV output voltage. These values should be in numerical order. The first row is reserved for column headers. Note: This code is very stupid, so make sure the format is correct!')
	parser.add_argument('-HVrampRate',type=float,default=1.0,help='Rate for fast HV voltage changes in V/s (default is 1 V/s). This is used when turning the HV up/down before/after data taking.')
	parser.add_argument('-HVrampUpdatePeriod',type=int,default=1,help='Period of time (in s) to wait between HV voltage changes while ramping. Default is 1 s. This is used when turning the HV up/down before/after data taking.')
	parser.add_argument('-HVdriftRate',type=float,default=0.0,help='Rate for HV voltage drifts in V/s (default is 0 V/s). This is used for slow HV changes during data taking.')
	parser.add_argument('-HVdriftUpdatePeriod',type=int,default=10,help='Period of time (in s) to wait between HV voltage changes while drifting. Default is 10 s. This is used for slow HV changes during data taking.')
	parser.add_argument('-HVpreBias',type=str,default='None',help='Prebias settings for HV. Should be in the form (Overbias %%)/(wait time min). As in 15/5 to overbias by 15%% for 5 minutes. Default is None.')
	#Series time	
	parser.add_argument('-tSeries',type=float,help='Run time for each data series in minutes')
	parser.add_argument('-NsubSeries',type=int,help='Number of subseries (individual MIDAS runs) to break each series into. This feature is for mitigating various DCRC issues which are reset by stopping/starting a new run. Default is None.')
	#Flashing
	parser.add_argument('-DCRCs2Flash',type=str,help='Comma-separated list of DCRC MIDAS numbers to use for flashing')
	parser.add_argument('-FlashDuration',type=float,default=30,help='Flash time in seconds. Default is 30 s.')
	parser.add_argument('-CoolDuration',type=float,default=30,help='Post flash cooldown time in minutes. Default is 30 min.')

	#So far this only has the oldMidas paths hardcoded
	
	args = parser.parse_args()

	###########################
	#Parse command line inputs
	###########################
#TODO: catch missing/incorrectly formatted arguments
	if (args.iDCRC is None) or (args.HVs is None) or (args.HVcalFile is None) or (args.HVrampRate is None) or (args.tSeries is None) or (args.DCRCs2Flash is None):
		parser.error('Error: missing required input. See pyChangeHV -h for info.')

	iDCRC = int(args.iDCRC)
	HVlist=[float(x) for x in args.HVs.split(',')]

	HVcalFile=args.HVcalFile
	
	HVrampRate=args.HVrampRate
	if args.HVrampUpdatePeriod<1.0:
		parser.error('Minimum HVrampUpdatePeriod is 1 s')
	else:
		HVrampUpdatePeriod=args.HVrampUpdatePeriod
	
	HVdriftRate=args.HVdriftRate
	if args.HVdriftUpdatePeriod<1.0:
		parser.error('Minimum HVdriftUpdatePeriod is 1 s')
	else:
		HVdriftUpdatePeriod=args.HVdriftUpdatePeriod

	if args.HVpreBias=='None':
		args.HVpreBias=None
	if not (args.HVpreBias is None):
		HVpreBiasPercent=float(args.HVpreBias.split('/')[0])
		HVpreBiasWait_sec=int(60.0*float(args.HVpreBias.split('/')[1]))

	tSeries_sec=round(args.tSeries*60.0)
	if args.NsubSeries is None:
		nSubSeries=1
	else:
		nSubSeries=args.NsubSeries
		tSeries_sec=round(float(tSeries_sec)/nSubSeries)

	DCRCs2FlashList=args.DCRCs2Flash.split(',')
	FlashDuration=args.FlashDuration
	CoolDuration_sec=round(args.CoolDuration*60.0)

	###########################
	#Sequence
	###########################
	print('HV bias Scan')
	print('COMMENT "Command to produce this script was: python '+" ".join(sys.argv[:])+'"')
	pyodbedit.write('/Logger/Write data','y')
	pyodbedit.write('/Logger/Run duration','0')

	print('run/flash/cooldown loop')
	#Assume we start at HV=0 with the power supply off	
	HVcurr=0.0
	for iHV, HV in enumerate(HVlist):
		###########
		#Set HV
		###########
		#Just have the pyChangeHV function handle this
		pyChangeHV.setHVpowerOnOff(iDCRC,'ON')

		changeHVargs=["-iDCRC",str(iDCRC),"-HVstart","0.0","-HVend",str(HV),"-HVcalFile",str(HVcalFile),\
				"-HVrampRate",str(HVrampRate),"-HVrampUpdatePeriod",str(HVrampUpdatePeriod)]
		#Prebias if it was called for and this is not a 0V series
		if (not (args.HVpreBias is None)) and HV!=0:
			changeHVargs.append("-HVpreBias")
			changeHVargs.append(str(args.HVpreBias))
		pyChangeHV.main(changeHVargs)
		###########
		#Take data
		###########
		print('Take Data. Set '+str(iHV+1)+'/'+str(len(HVlist)))
		pyodbedit.write('/Seriesinfo/Duration (s)',str(tSeries_sec))

		for iSubSeries in range(nSubSeries):
			if nSubSeries>1:
				print('SubSeries '+str(iSubSeries+1)+'/'+str(nSubSeries))

			print('Start Run')
			pyodbedit.runstart()

			if HVdriftRate==0.0:
				#No HV drifting
				print('Waiting'+ str(tSeries_sec))
				time.sleep(tSeries_sec)
			else:
				#Drift HV during data taking
				print('Drifting HV at '+str(HVdriftRate)+' V/s')
				HVfinal=HV+HVdriftRate*tSeries_sec
				changeHVargs=["-iDCRC",str(iDCRC),"-HVstart",str(HV),"-HVend",str(HVfinal),"-HVcalFile",str(HVcalFile),\
							"-HVrampRate",str(HVdriftRate),"-HVrampUpdatePeriod",str(HVdriftUpdatePeriod)]
				pyChangeHV.main(changeHVargs)
				HV=HVfinal

			print('Stop Run')
			pyodbedit.runstop()
			

		###########
		#Set HV=0
		###########
		changeHVargs=["-iDCRC",str(iDCRC),"-HVstart",str(HV),"-HVend","0.0","-HVcalFile",str(HVcalFile),\
				"-HVrampRate",str(HVrampRate),"-HVrampUpdatePeriod",str(HVrampUpdatePeriod)]
		pyChangeHV.main(changeHVargs)
		#pyChangeHV.setHVpowerOnOff('OFF') # This seems to cause channels to rail. Just dial it down to 0

		###########
		#Flash & cooldown
		###########
		print('Flash and cooldown')
		#Save 15V power settings and enable
		DCRC_15VPowerList=pyflash.get15VPowerEnable(DCRCs2FlashList)
		pyflash.turn15VPowerEnableOn(DCRCs2FlashList)

		#Flash
		pyflash.enableLEDs(DCRCs2FlashList,1)
		print('Wait '+ str(FlashDuration)+ ' sec')
		time.sleep(FlashDuration)
		pyflash.enableLEDs(DCRCs2FlashList,0)
		
		#Restore previous 15V power state
		pyflash.set15VPowerEnable(DCRCs2FlashList,DCRC_15VPowerList)
		#Cooldown
		print('Cooldown '+ str(CoolDuration_sec)+' sec')
		time.sleep(CoolDuration)
		print('')

	
	#Return to normal settings
	print('')
	print('Restore normal settings')
	pyodbedit.write('/Logger/Write data','n')

