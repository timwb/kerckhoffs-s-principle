#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import os, sys, daemon, daemon.pidfile, signal, argparse, logging, logging.handlers, time, json, request
from datetime import datetime

#Broadcom GPIO numbers
gpioDeurbel = 17

def program_cleanup():
	logger.debug(scriptname+" Cleanup")
	# close file handles, print stuff to log

def terminate():
	logger.debug(scriptname+" Recevied SIGHUP")

def reload_program_config():
	logger.debug(scriptname+" Received config signal")
	# i think this is sigusr 1

def setup():
	shmf = ()
	return shmf

def main():
	logger.debug("arrived at main()")
	
	while True:
		echo("bla")
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
