# Program to issue odbedit commands to manipulate MIDAS to take Qbias scan data without using the Sequencer
#
#Nick Mast 10/2019
#
import sys
import argparse
from argparse import ArgumentParser, ArgumentTypeError

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
	parser.add_argument('-DCRC_S1S2',type=str,help='MIDAS DCRC number of boards controlling Side1 and Side2 Q biases. Format at Side1DCRC/Side2DCRC. e.g. 3/1 for DCRC3 on side1 and DCRC1 on side2.')
	#Voltage Biases
	parser.add_argument('-Vs',type=str,help='Bias voltages in desired run order. Format as (Side1 V1/Side2 V1),(Side1 V2/Side2 V2) etc. e.g. (0/0),(5/-5),(10/-10)')
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
	if (args.iDCRCs is None) or (args.Vs is None) or (args.tSeries is None) or (args.DCRCs2Flash is None):
		parser.error('Error: missing required input. See pyChangeHV -h for info.')

	#TODO: Make sure these are legitimate DCRC numbers
	DCRC_S1=args.DCRC_S1S2.split('/')[0]
	DCRC_S2=args.DCRC_S1S2.split('/')[1]

	#Parse Vs list of the format: (V11/V21),(V12/V22),(V13/V23)
	args.Vs.replace(" ","")
	Vlist=re.findall("\(([+-]?\d*\.?\d+)/([+-]?\d*\.?\d+)\)",args.Vs)
	Vlist=numpy.array(Vlist).astype(numpy.float)
	
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
	print('Qbias Scan')
	print('COMMENT "Command to produce this script was: python '+" ".join(sys.argv[:])+'"')
	pyodbedit.write('/Logger/Write data','y')
	pyodbedit.write('/Logger/Run duration',str(tSeries_sec))

	print('run/flash/cooldown loop')
	for iV, V in enumerate(Vlist):
		#Set Qbias
		pyodbedit.write('/Equipment/Tower01/Settings/DCRC'+str(DCRC_S1)+'/Charge/Bias (V)[0]',str(V[0]))
		pyodbedit.write('/Equipment/Tower01/Settings/DCRC'+str(DCRC_S1)+'/Charge/Bias (V)[1]',str(V[0]))
		
		pyodbedit.write('/Equipment/Tower01/Settings/DCRC'+str(DCRC_S2)+'/Charge/Bias (V)[0]',str(V[1]))
		pyodbedit.write('/Equipment/Tower01/Settings/DCRC'+str(DCRC_S1)+'/Charge/Bias (V)[1]',str(V[1]))

		###########
		#Take data
		###########
		print('Take Data. Set '+str(iV+1)+'/'+str(len(Vlist)))
		pyodbedit.write('/Seriesinfo/Duration (s)',str(tSeries_sec))

		for iSubSeries in range(nSubSeries):
			if nSubSeries>1:
				print('SubSeries '+str(iSubSeries+1)+'/'+str(nSubSeries))

			print('Start Run')
			pyodbedit.runstart()

			print('Waiting'+ str(tSeries_sec))
			time.sleep(tSeries_sec)

			print('Stop Run')
			pyodbedit.runstop()
			
		#Set Qbias = 0
		pyodbedit.write('/Equipment/Tower01/Settings/DCRC'+str(DCRC_S1)+'/Charge/Bias (V)[0]',str(0))
		pyodbedit.write('/Equipment/Tower01/Settings/DCRC'+str(DCRC_S1)+'/Charge/Bias (V)[1]',str(0))
		
		pyodbedit.write('/Equipment/Tower01/Settings/DCRC'+str(DCRC_S2)+'/Charge/Bias (V)[0]',str(0))
		pyodbedit.write('/Equipment/Tower01/Settings/DCRC'+str(DCRC_S1)+'/Charge/Bias (V)[1]',str(0))

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
		print('')

	
	#Return to normal settings
	print('')
	print('Restore normal settings')
	pyodbedit.write('/Logger/Write data','n')
	print('Done')
