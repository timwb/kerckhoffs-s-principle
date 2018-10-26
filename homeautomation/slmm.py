#!/usr/bin/env python3
# -*- coding: utf-8 -*-
import sys, os, daemon, daemon.pidfile, signal, argparse, logging, logging.handlers, json, calendar
import time, serial, re, collections

from datetime import datetime

#setup reasonable defaults
serialport = '/dev/ttySC0'

# Leveringstarief, energiebelasting en opslag duurzaame energie
kwhhprice = (0.04900 + 0.10458 + 0.01320)*1.21
kwhlprice = (0.03700 + 0.10458 + 0.01320)*1.21
# gasregio 3 leveringtarief, energiebelasting en opslag duurzame energie
gasprice =  (0.22200 + 0.26001 + 0.02850)*1.21
# Standing charge per month
# Tussen haakjes: aansluitvergoeding, vastrecht, capaciteitstarief, meterhuur, belastingvermindering
stdchrge = 0.99 + (18.9940 + 18.00 + 130.8800 + 28.01 - 308.54)*1.21/12
stdchrgg = 0.99 + (26.8900 + 18.00 +  84.1800 + 20.48         )*1.21/12

# Correctiefactor gas
gascorr = 1.00106

def program_cleanup():
	logger.debug("Cleanup")
	# close file handles, print stuff to log


def terminate():
	logger.debug("Recevied SIGHUP")


def reload_program_config():
	logger.debug("Received config signal")
	# i think this is sigusr 1


def setup():
	# get ourselves a serial port
	p1conn = serial.Serial(
		baudrate=9600,
		bytesize=serial.SEVENBITS,
		parity=serial.PARITY_EVEN,
		stopbits=serial.STOPBITS_ONE,
		timeout=0.5,
		exclusive=True
	)
	p1conn.port = serialport
	try:
		p1conn.open()
	except serial.SerialException:
		logger.critical("SerialException. help!!")
	# create file handles before daemonization
	shmf = (
		open('/dev/shm/slmm', 'w'),
		open('/var/local/slmmstate.json', 'r+'),
		os.fdopen(p1conn.fd)
		)
	return shmf, p1conn


def initstats():
	stats = {
			'5mavgpwr':  0.0,
			'kwhhtoday': 0.0,
			'kwhltoday': 0.0,
			'kwhctoday': 0.0,
			'gastoday':  0.0,
			'gasctoday': 0.0,
			'kwhhyesterday': 0.0,
			'kwhlyesterday': 0.0,
			'kwhcyesterday': 0.0,
			'gasyesterday':  0.0,
			'gascyesterday': 0.0,
			'kwhhdaybefore': 0.0,
			'kwhldaybefore': 0.0,
			'kwhcdaybefore': 0.0,
			'gasdaybefore':  0.0,
			'gascdaybefore': 0.0,
			'totalkwhhnow':  0.0,
			'totalkwhlnow':  0.0,
			'totalgasnow':   0.0,
			'nowtimestamp':  0.0,
			'totalkwhhatmidnight':   0.0,
			'totalkwhlatmidnight':   0.0,
			'totalgasatmidnight':    0.0,
			'lastmidnighttimestamp': 0.0,
			'lastnumrmessage':         0,
			'lastnumrmessagetimestamp': 0.0,
			'lasttextmessage':           '',
			'lasttextmessagetimestamp': 0.0
		}
	# Read stats from disk and parse if valid
	shmf[1].seek(0, 0)
	try:
		diskstats = json.load(shmf[1])
	except:
		logger.info("State file missing or invalid, state not restored")
		return stats
	
	logger.info("State file loaded from disk")
	stats['lastmidnighttimestamp']    = diskstats.get('lastmidnighttimestamp', 0.0)
	
	if stats['lastmidnighttimestamp'] != 0.0 and datetime.fromtimestamp(time.time()).strftime('%y%m%d') == datetime.fromtimestamp(stats['lastmidnighttimestamp']).strftime('%y%m%d') :
		logger.info("State valid, continuing where we left off")
		stats['kwhhyesterday']             = diskstats.get('kwhhyesterday', 0.0)
		stats['kwhlyesterday']             = diskstats.get('kwhlyesterday', 0.0)
		stats['gasyesterday']              = diskstats.get('gasyesterday',  0.0)
		stats['kwhhdaybefore']             = diskstats.get('kwhhdaybefore', 0.0)
		stats['kwhldaybefore']             = diskstats.get('kwhldaybefore', 0.0)
		stats['gasdaybefore']              = diskstats.get('gasdaybefore',  0.0)
		stats['totalkwhhatmidnight']       = diskstats.get('totalkwhhatmidnight', 0.0)
		stats['totalkwhlatmidnight']       = diskstats.get('totalkwhlatmidnight', 0.0)
		stats['totalgasatmidnight']        = diskstats.get('totalgasatmidnight',  0.0)
		year  = int(datetime.fromtimestamp(stats['lastmidnighttimestamp']-60).strftime('%Y'))
		month = int(datetime.fromtimestamp(stats['lastmidnighttimestamp']-60).strftime('%m'))
		daysinmonth = calendar.monthrange(year, month)[1]
		stats['kwhcyesterday'] = (stdchrge/daysinmonth) + kwhhprice*stats['kwhhyesterday'] + kwhlprice*stats['kwhlyesterday']
		stats['gascyesterday'] = (stdchrgg/daysinmonth) + gasprice *stats['gasyesterday']
		year  = int(datetime.fromtimestamp(stats['lastmidnighttimestamp']-86460).strftime('%Y'))
		month = int(datetime.fromtimestamp(stats['lastmidnighttimestamp']-86460).strftime('%m'))
		daysinmonth = calendar.monthrange(year, month)[1]
		stats['kwhcdaybefore'] = (stdchrge/daysinmonth) + kwhhprice*stats['kwhhdaybefore'] + kwhlprice*stats['kwhldaybefore']
		stats['gascdaybefore'] = (stdchrgg/daysinmonth) + gasprice *stats['gasdaybefore']	
	else:
		logger.info("State data is stale, ignoring")
		stats['lastmidnighttimestamp'] = 0.0
	
	stats['lastnumrmessage']          = diskstats.get('lastnumrmessage', 0.0)
	stats['lastnumrmessagetimestamp'] = diskstats.get('lastnumrmessagetimestamp', 0.0)
	stats['lasttextmessage']          = diskstats.get('lasttextmessage', 0.0)
	stats['lasttextmessagetimestamp'] = diskstats.get('lasttextmessagetimestamp', 0.0)
	
	return stats


def decodetelegram(telegram, ttimestamp):
	res = dict()
	m = dict()
	n = -1
	# validate, build dictionary from results (res) and parse to message (m)
	# results is a dictionary of OBIS reference code and a tuple of value and line number
	for l in telegram:
		n = n+1
		tmp = tcode.findall(l.decode('ascii').strip())
		if tmp is not None and len(tmp) != 0:
			res[tmp[0][0]] = (tmp[0][1], n)
	
	m['timestamp']    = ttimestamp
	#res['0-0:96.1.1'][0] # Meter s/n
	m['leveringlaag'] = float(res['1-0:1.8.1'][0].replace("*kWh",""))
	m['leveringhoog'] = float(res['1-0:1.8.2'][0].replace("*kWh",""))
	m['teruglvrlaag'] = float(res['1-0:2.8.1'][0].replace("*kWh",""))
	m['teruglvrhoog'] = float(res['1-0:2.8.2'][0].replace("*kWh",""))
	m['laagtarief']   = res['0-0:96.14.0'][0] == '0001'
	m['hvermogeninw'] = int(float(res['1-0:1.7.0'][0].replace("*kW",""))*1000)
	m['hterugvermog'] = int(float(res['1-0:2.7.0'][0].replace("*kW",""))*1000)
	if res['0-0:96.13.1'][0] == '':
		m['numrmessage'] = 0
	else:
		m['numrmessage'] = int(res['0-0:96.13.1'][0])
		logger.info("Received numerical message: "+lastnumrmessage[0])
	m['textmessage']  = res['0-0:96.13.0'][0]
	if m['textmessage'] != '':
		logger.info("Received text message: "+lasttextmessage[0])
	#res['0-0:96.1.1'] # Gasmeter s/n
	#res['0-1:24.1.0'] # Num devices on meter bus
	gas = res['0-1:24.3.0'][0].split(')(')
	m['gastimestamp'] = datetime.strptime(gas[0], '%y%m%d%H%M%S').timestamp()
	m['gasverbruikl'] = int(float(telegram[res['0-1:24.3.0'][1]+1].decode('ascii').strip()[1:-1])*1000)
	
	return m, res


def updatestats(stats={}, m={}, pwrlog=collections.deque(maxlen=30), nextday=False):
	# Compute stats, 24h counters
	dirtystate = False
	
	# Write some 5-minute sliding window average (for use by Munin)
	pwrlog.append(m['hvermogeninw']-m['hterugvermog'])
	stats['5mavgpwr'] = 0
	for p in pwrlog:
		stats['5mavgpwr'] += p / len(pwrlog)
	
	stats['totalkwhhnow'] = m['leveringhoog'] - m['teruglvrhoog']
	stats['totalkwhlnow'] = m['leveringlaag'] - m['teruglvrlaag']
	stats['totalgasnow']  = m['gasverbruikl'] / 1000
	
	stats['nowtimestamp'] = m['timestamp']
	
	if nextday:
		logger.debug("It's a brand new day!")
		stats['kwhhdaybefore'] = stats['kwhhyesterday']
		stats['kwhldaybefore'] = stats['kwhlyesterday']
		stats['kwhcdaybefore'] = stats['kwhcyesterday']
		stats['gasdaybefore'] = stats['gasyesterday']
		stats['gascdaybefore'] = stats['gascyesterday']
		if stats['totalkwhhatmidnight'] != 0:
			stats['kwhhyesterday'] = stats['totalkwhhnow'] - stats['totalkwhhatmidnight']
			stats['kwhlyesterday'] = stats['totalkwhlnow'] - stats['totalkwhlatmidnight']
			stats['gasyesterday']  = stats['totalgasnow']  - stats['totalgasatmidnight']
			year  = int(datetime.fromtimestamp(stats['lastmidnighttimestamp']).strftime('%Y'))
			month = int(datetime.fromtimestamp(stats['lastmidnighttimestamp']).strftime('%m'))
			daysinmonth = calendar.monthrange(year, month)[1]
			stats['kwhcyesterday'] = (stdchrge/daysinmonth) + kwhhprice*stats['kwhhyesterday'] + kwhlprice*stats['kwhlyesterday']
			stats['gascyesterday'] = (stdchrgg/daysinmonth) + gasprice *stats['gasyesterday']
		else:
			logger.debug("First new day, no prior usage data")
		stats['totalkwhhatmidnight'] = stats['totalkwhhnow']
		stats['totalkwhlatmidnight'] = stats['totalkwhlnow']
		stats['totalgasatmidnight']  = stats['totalgasnow']	
		stats['lastmidnighttimestamp'] = stats['nowtimestamp']
		dirtystate = True
	
	if stats['totalkwhhatmidnight'] != 0:
		stats['kwhhtoday'] = stats['totalkwhhnow'] - stats['totalkwhhatmidnight']
		stats['kwhltoday'] = stats['totalkwhlnow'] - stats['totalkwhlatmidnight']
		stats['gastoday']  = stats['totalgasnow']  - stats['totalgasatmidnight']
		year  = int(datetime.fromtimestamp(stats['nowtimestamp']).strftime('%Y'))
		month = int(datetime.fromtimestamp(stats['nowtimestamp']).strftime('%m'))
		daysinmonth = calendar.monthrange(year, month)[1]
		stats['kwhctoday'] = (stdchrge/daysinmonth) + kwhhprice*stats['kwhhtoday'] + kwhlprice*stats['kwhltoday']
		stats['gasctoday'] = (stdchrgg/daysinmonth) + gasprice *stats['gastoday'] * gascorr
	
	if m['numrmessage'] != 0:
		stats['lastnumrmessage']          = m['numrmessage']
		stats['lastnumrmessagetimestamp'] = m['timestamp']
		dirtystate = True
	
	if m['textmessage'] != '':
		stats['lasttextmessage']          = m['textmessage']
		stats['lasttextmessagetimestamp'] = m['timestamp']
		dirtystate = True
	
	return stats, dirtystate


def writedata(stats={}, m={}, t="", dirtystate=False):
	# json file for home automation
	shmf[0].seek(0, 0)
	jsondata = {}
	jsondata['lastmessage'] = m
	jsondata['stats'] = stats
	tdec=[]
	for l in t:
		tdec.append(l.decode('ISO-8859-15'))
	jsondata['telegram'] = tdec
	json.dump(jsondata, shmf[0])
	shmf[0].truncate()
	shmf[0].flush()
	
	# flush json file with state information to disk only when needed
	if dirtystate:
		logger.info("Writing new state data")
		shmf[1].seek(0, 0)
		json.dump(stats, shmf[1])
		shmf[1].truncate()
		shmf[1].flush()


def main():
	# do stuff
	logger.debug("arrived at main()")
	m = dict()
	pwrlog = collections.deque(maxlen=30)
	ttimestamp = 0.0
	previousttimestamp = 0.0
	nextday = False
	dirtystate = False
	
	#try:
	#	p1conn.open()
	#except serial.SerialException:
	#	logger.critical("SerialException. help!!")
	
	stats = initstats()
	
	# DSMR sends a 'Telegram' every 10 seconds with the current meter reading.
	# let Serial.readlines() do the magic and use the remaining time to process the telegram
	while True:
		telegram = p1conn.readlines()
		time.sleep(0.01)
		if telegram==[]: continue # Poor man's idle loop
		if not tstart.match(telegram[0].decode('ascii').strip()):
			logger.warning('Invalid telegram start "'+telegram[0].decode('ascii').strip()+'", ignoring current telegram')
			continue
		if telegram[len(telegram)-1].decode('ascii').strip()[0] != '!':
			# Todo: Implement telegram CRC checking
			logger.warning('Invalid telegram end "'+telegram[len(telegram)-1].decode('ascii').strip()+'", ignoring current telegram')
			continue
		
		ttimestamp = time.time()
		
		# Decode telegram
		m, res = decodetelegram(telegram, ttimestamp)
		
		if previousttimestamp != 0.0:
			nextday = datetime.fromtimestamp(ttimestamp).strftime('%d') != datetime.fromtimestamp(previousttimestamp).strftime('%d')
		previousttimestamp = ttimestamp
		
		# Update stats
		stats, dirtystate = updatestats(stats, m, pwrlog, nextday)
		
		# Writedata
		writedata(stats, m, telegram, dirtystate)
		dirtystate = False


if __name__ == '__main__':
	scriptname = os.path.splitext(os.path.basename(__file__))[0]
	pidfullpath = '/var/run/'+scriptname+'.pid'
	parser = argparse.ArgumentParser()
	parser.add_argument('-f', '--foreground', help="Do not daemonize, log to stdout", action='store_true')
	parser.add_argument('-s', '--serialport', help="Serial port to use (default: "+serialport+")")
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
	
	if not args.serialport is None:
		serialport = args.serialpot
	
	if not args.pidfile is None:
		pidfullpath = args.pidfile
	
	if not args.logfile is None:
		fh = logging.FileHandler(args.logfile)
		fh.setLevel(own_loglevel)
		fh.setFormatter(formatter)
		logger.addHandler(fh)
	
	tstart = re.compile('^\/')
	tcode  = re.compile('^([0-9]-[0-9]:[0-9]{1,2}.[0-9]{1,2}.[0-9]{1,2})\((.*)\)')
	
	if args.foreground:
		ch = logging.StreamHandler()
		ch.setLevel(own_loglevel)
		ch.setFormatter(formatter)
		logger.addHandler(ch)
		logger.info("*** "+scriptname+" running in foreground. ***")
		shmf, p1conn = setup()
		main()
	
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
		
		shmf, p1conn = setup()
		
		pidfile = daemon.pidfile.PIDLockFile(pidfullpath)
		context = daemon.DaemonContext(
			umask=0o002,
			pidfile=pidfile,
			detach_process=True
			)
		context.signal_map = {
			signal.SIGTERM: program_cleanup,
			signal.SIGHUP:  terminate,
			signal.SIGUSR1: reload_program_config
			}
		context.files_preserve = list(shmf)
		if not args.logfile is None:
			context.files_preserve.append(fh.stream)
		# This is when we fork.
		print("***  "+scriptname+" forking to background. ***")
		with context:
			main()
