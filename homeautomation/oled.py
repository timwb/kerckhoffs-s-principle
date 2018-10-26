#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import os, sys, daemon, daemon.pidfile, signal, argparse, logging, logging.handlers, time, json, locale
from datetime import datetime

from luma.core.interface.serial import spi
from luma.core.render import canvas
from luma.oled.device import sh1106

from PIL import ImageFont

#Broadcom GPIO numbers
gpioDC = 23
gpioRST = 25

# correctiefactor luchtvochtigheidsmeter
crestacorr = 1.06741573

def program_cleanup():
	logger.debug(scriptname+" Cleanup")
	# close file handles, print stuff to log


def terminate():
	logger.debug(scriptname+" Recevied SIGHUP")


def reload_program_config():
	logger.debug(scriptname+" Received config signal")
	# i think this is sigusr 1


def setup():
	shmf = (
		open('/dev/shm/slmm', 'r'),
		open('/dev/shm/cresta', 'r')
		)
	font = ImageFont.truetype('/usr/local/share/fonts/truetype/Pixel-UniCode.ttf',16)
	return shmf, font

def getdevice():
	#/dev/spidev0.0
	serial = spi(device=0, port=0, bus_speed_hz=4000000, transfer_size=4096, gpio_DC=gpioDC, gpio_RST=gpioRST)
	device = sh1106(serial, rotate=0)
	device.contrast(31)
	return device


def updatedata(screendata={}):
	shmf[0].seek(0, 0)
	slmmdata = json.load(shmf[0])
	shmf[1].seek(0, 0)
	crestadata = json.load(shmf[1])
	
	screendata['crestastring']= "N/A"
	if crestadata.get('model', "") == "HIDEKI TS04 sensor" and crestadata.get('rc', -1) == 7:
		t  = crestadata.get('temperature_C')
		rh = crestadata.get('humidity')*crestacorr
		ah = (6.112 * 2.7182818284 ** ((17.67 * t) / (t + 243.5)) * rh * 2.1674 ) / (273.15 + t)
		screendata['crestastring'] = (
			"T " + "{:.1f}".format(t) +
			"°C, RH " + "{:2.0f}".format(rh) +
			"%, AH " + "{:.2f}".format(ah) + " g/ℓ"
		)
	screendata['datestring']          = "Vandaag " + datetime.fromtimestamp(time.time()).strftime('%a %d %b')
	screendata['timestring']          = datetime.fromtimestamp(time.time()).strftime('%H:%M')
	screendata['yesterdaydatestring'] = datetime.fromtimestamp(slmmdata['stats']['lastmidnighttimestamp'] - 60)   .strftime('%d-%m')
	screendata['daybeforedatestring'] = datetime.fromtimestamp(slmmdata['stats']['lastmidnighttimestamp'] - 86460).strftime('%d-%m')
	screendata['kwhyesterdaystring']  = "{:.2f}".format(slmmdata['stats']['kwhhyesterday']+slmmdata['stats']['kwhlyesterday'])
	screendata['kwhcyesterdaystring'] = "{:.2f}".format(slmmdata['stats']['kwhcyesterday'])
	screendata['gasyesterdaystring']  = "{:.3f}".format(slmmdata['stats']['gasyesterday'])
	screendata['gascyesterdaystring'] = "{:.2f}".format(slmmdata['stats']['gascyesterday'])
	screendata['kwhdaybeforestring']  = "{:.2f}".format(slmmdata['stats']['kwhhdaybefore']+slmmdata['stats']['kwhldaybefore'])
	screendata['kwhcdaybeforestring'] = "{:.2f}".format(slmmdata['stats']['kwhcdaybefore'])
	screendata['gasdaybeforestring']  = "{:.3f}".format(slmmdata['stats']['gasdaybefore'])
	screendata['gascdaybeforestring'] = "{:.2f}".format(slmmdata['stats']['gascdaybefore'])
	
	return screendata


def updatedisplay(device, screendata={}):
	with canvas(device) as draw:
		draw.text((0    , -5), screendata['datestring'],           font=font, fill="white")
		w = draw.textsize(     screendata['timestring'],           font=font)[0]
		draw.text((124-w, -5), screendata['timestring'],           font=font, fill="white")
		
		draw.text((0    ,  7), screendata['yesterdaydatestring'],  font=font, fill="white")
		w = draw.textsize(     screendata['kwhyesterdaystring'],   font=font)[0]
		draw.text((62-w ,  7), screendata['kwhyesterdaystring'],   font=font, fill="white")
		draw.text((66   ,  7), "kWh,",                             font=font, fill="white")
		draw.text((92   ,  7), "€",                                font=font, fill="white")
		w = draw.textsize(     screendata['kwhcyesterdaystring'],  font=font)[0]
		draw.text((128-w,  7), screendata['kwhcyesterdaystring'],  font=font, fill="white")
		
		draw.text((0    , 17), screendata['yesterdaydatestring'],  font=font, fill="white")
		w = draw.textsize(     screendata['gasyesterdaystring'],   font=font)[0]
		draw.text((62-w,  17), screendata['gasyesterdaystring'],   font=font, fill="white")
		draw.text((66   , 17), "m³,",                              font=font, fill="white")
		draw.text((92   , 17), "€",                                font=font, fill="white")
		w = draw.textsize(     screendata['gascyesterdaystring'],  font=font)[0]
		draw.text((128-w, 17), screendata['gascyesterdaystring'],  font=font, fill="white")
		
		draw.text((0    , 27), screendata['daybeforedatestring'],  font=font, fill="white")
		w = draw.textsize(     screendata['kwhdaybeforestring'],   font=font)[0]
		draw.text((62-w , 27), screendata['kwhdaybeforestring'],   font=font, fill="white")
		draw.text((66   , 27), "kWh,",                             font=font, fill="white")
		draw.text((92   , 27), "€",                                font=font, fill="white")
		w = draw.textsize(     screendata['kwhcdaybeforestring'],  font=font)[0]
		draw.text((128-w, 27), screendata['kwhcdaybeforestring'],  font=font, fill="white")
		
		draw.text((0    , 37), screendata['daybeforedatestring'],  font=font, fill="white")
		w = draw.textsize(     screendata['gasdaybeforestring'],   font=font)[0]
		draw.text((62-w,  37), screendata['gasdaybeforestring'],   font=font, fill="white")
		draw.text((66   , 37), "m³,",                              font=font, fill="white")
		draw.text((92   , 37), "€",                                font=font, fill="white")
		w = draw.textsize(     screendata['gascdaybeforestring'],  font=font)[0]
		draw.text((128-w, 37), screendata['gascdaybeforestring'],  font=font, fill="white")
		
		draw.text((0    , 48), screendata['crestastring'],         font=font, fill="white")


def main():
	logger.debug("arrived at main()")
	
	locale.setlocale(locale.LC_ALL, 'nl_NL.utf8')
	
	screendata = dict()
	device = getdevice()
	
	# Update display every whole minute (to make sure clock updates are nicely synced)
	while True:
		screendata = updatedata()
		updatedisplay(device, screendata)
		nextminute = datetime.fromtimestamp(time.time()+60).strftime('%y-%m-%d %H:%M')
		sleepuntil = datetime.strptime(nextminute, '%y-%m-%d %H:%M').timestamp()
		time.sleep(sleepuntil-time.time())


if __name__ == "__main__":
	scriptname = os.path.splitext(os.path.basename(__file__))[0]
	pidfullpath = '/var/run/'+scriptname+'.pid'
	parser = argparse.ArgumentParser()
	parser.add_argument('-f', '--foreground', help="Do not daemonize, log to stdout", action='store_true')
	parser.add_argument('-p', '--pidfile',    help="Pidfile to use (default: "+pidfullpath+")")
	parser.add_argument('-l', '--logfile',    help="Path to logfile (default: log to syslog only)")
	parser.add_argument('-L', '--loglevel',   help="Logging level := { CRITICAL | ERROR | WARNING | INFO | DEBUG } (default: INFO)")
	args = parser.parse_args()
	
	logger = logging.getLogger()
	
	if   args.loglevel == 'CRITICAL':
		own_loglevel = logging.CRITICAL
	elif args.loglevel == 'ERROR':
		own_loglevel = logging.ERROR
	elif args.loglevel == 'WARNING':
		own_loglevel = logging.WARNING
	elif (args.loglevel == 'INFO' or args.loglevel is None):
		own_loglevel = logging.INFO
	elif args.loglevel == 'DEBUG':
		own_loglevel = logging.DEBUG
	else:
		print("Unknown Log level "+args.loglevel)
		exit(1)
	
	logger.setLevel(own_loglevel)
	formatter = logging.Formatter('%(asctime)s - %(levelname)s - %(message)s')
	
	if not args.pidfile is None:
		pidfullpath = args.pidfile
	
	if not args.logfile is None:
		fh = logging.FileHandler(args.logfile)
		fh.setLevel(own_loglevel)
		fh.setFormatter(formatter)
		logger.addHandler(fh)
	
	if args.foreground:
		ch = logging.StreamHandler()
		ch.setLevel(own_loglevel)
		ch.setFormatter(formatter)
		logger.addHandler(ch)
		logger.info("*** "+scriptname+" running in foreground. ***")
		
		try:
			shmf, font = setup()
			main()
		except KeyboardInterrupt:
			pass
	
	else:
		# daemonize and log to syslog
		sh = logging.handlers.SysLogHandler(
			facility=logging.handlers.SysLogHandler.LOG_DAEMON,
			address = '/dev/log'
			)
		sh.setLevel(own_loglevel)
		formatter = logging.Formatter(scriptname + ': %(message)s')
		sh.setFormatter(formatter)
		logger.addHandler(sh)

		pidfile = daemon.pidfile.PIDLockFile(pidfullpath)
		context = daemon.DaemonContext(
			#working_directory='/usr/local/share/timscripts',
			umask=0o002,
			pidfile=pidfile,
			detach_process=True
			)
		context.signal_map = {
			signal.SIGTERM: program_cleanup,
			signal.SIGHUP:  terminate,
			signal.SIGUSR1: reload_program_config
			}
		shmf, font = setup()
		context.files_preserve = list(shmf)
		if not args.logfile is None:
			context.files_preserve.append(fh.stream)
		# This is when we fork.
		print("***  "+scriptname+" forking to background. ***")
		with context:
			main()
