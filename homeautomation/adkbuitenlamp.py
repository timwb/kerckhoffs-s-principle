#!/usr/bin/env python3
# -*- coding: utf-8 -*-
import sys, os, daemon, daemon.pidfile, signal, argparse, logging, logging.handlers
import sched, time, datetime, sunrise, pytz
import wiringpi

#setup reasonable defaults
scriptname = os.path.splitext(os.path.basename(__file__))[0]
pidfullpath = '/var/run/'+scriptname+'.pid'

# Location of your house
lat  = 0.0
long = 0.0

pin1 = 5
pin2 = 6

def program_cleanup():
    logger.debug("cleanup")
    wiringpi.digitalWrite(pin1, 0)
    wiringpi.digitalWrite(pin2, 0)
    wiringpi.pinMode(pin1, 0)
    wiringpi.pinMode(pin2, 0)
    # close file handles, print stuff to log

def terminate():
    logger.debug("SIGHUP")

def reload_program_config():
    logger.debug("config")
    # i think this is sigusr 1

def lightson():
    logger.debug("lightson")
    wiringpi.digitalWrite(pin1, 1)
    wiringpi.digitalWrite(pin2, 1)

def lightsoff():
    logger.debug("lightsoff")
    wiringpi.digitalWrite(pin1, 0)
    wiringpi.digitalWrite(pin2, 0)

# called when the sun sets
def sunsetevent():
    global sunriseclass
    global scheduler
    lightson()
    tomorrow = datetime.datetime.fromtimestamp(time.time()+86400)
    testtime = pytz.timezone('Europe/Amsterdam').localize(datetime.datetime.combine(tomorrow.date(), datetime.time(hour=6, minute=0, second=0, microsecond=0)))
    sunrisetomorrow = sunriseclass.sunrise(when = testtime)
    nextsunrise = pytz.timezone('Europe/Amsterdam').localize(datetime.datetime.combine(tomorrow.date(), sunrisetomorrow))
    logger.debug('Scheduling next sunrise event at: '+str(nextsunrise))
    # wake me up when the sun rises
    scheduler.enterabs(nextsunrise.timestamp(), 1, sunriseevent)
    scheduler.run()

# called when the sun rises
def sunriseevent():
    global sunriseclass
    global scheduler
    lightsoff()
    today = datetime.datetime.now()
    testtime = pytz.timezone('Europe/Amsterdam').localize(datetime.datetime.combine(today.date(), datetime.time(hour=18, minute=0, second=0, microsecond=0)))
    sunsettoday = sunriseclass.sunset(when = testtime)
    nextsunset = pytz.timezone('Europe/Amsterdam').localize(datetime.datetime.combine(today.date(), sunsettoday))
    logger.debug('Scheduling next sunset event at: '+str(nextsunset))
    # wake me up when the sun sets
    scheduler.enterabs(nextsunset.timestamp(), 1, sunsetevent)
    scheduler.run()

def main():
    global sunriseclass
    global scheduler
    global pin1
    global pin2
    # setup
    logger.info(scriptname+" starting")
    wiringpi.wiringPiSetupGpio()
    wiringpi.pinMode(pin1, 1)
    wiringpi.pinMode(pin2, 1)
    sunriseclass = sunrise.sun(lat=lat,long=long)
    scheduler = sched.scheduler(time.time, time.sleep)
    # calculate times for today
    now = datetime.datetime.now()
    testtime = pytz.timezone('Europe/Amsterdam').localize(datetime.datetime.combine(now.date(), datetime.time(hour=12, minute=0, second=0, microsecond=0)))
    sunrisetoday = sunriseclass.sunrise(when = testtime)
    sunsettoday = sunriseclass.sunset(when = testtime)
    # determine current state
    if sunrisetoday < now.time():
        if now.time() < sunsettoday:
            logger.info("sun is up")
            lightsoff()
            nextsunset = pytz.timezone('Europe/Amsterdam').localize(datetime.datetime.combine(now.date(), sunsettoday))
            logger.info('Scheduling next sunset event at: '+str(nextsunset))
            scheduler.enterabs(nextsunset.timestamp(), 1, sunsetevent)
            scheduler.run()
        else:
            logger.info("sun is down, evening")
            sunsetevent()
    else:
        logger.info("sun is down, night or morning")
        lightson()
        nextsunrise = pytz.timezone('Europe/Amsterdam').localize(datetime.datetime.combine(now.date(), sunrisetoday))
        logger.info('Scheduling next sunrise event at: '+str(nextsunrise))
        scheduler.enterabs(nextsunrise.timestamp(), 1, sunriseevent)
        scheduler.run()

if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('-f', '--foreground',        help="Do not daemonize, log to stdout", action='store_true')
    parser.add_argument('-p', '--pidfile',           help="Pidfile to use (default: "+pidfullpath+")")
    #parser.add_argument('-d', '--working-directory', help="Working directory")
    parser.add_argument('-l', '--logfile',           help="Path to logfile (default: log to syslog only)")
    parser.add_argument('-L', '--loglevel',          help="Logging level := { CRITICAL | ERROR | WARNING | INFO | DEBUG } (default: INFO)")
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
        main()

    else:
        # daemonize and log to syslog
        sh = logging.handlers.SysLogHandler(
            facility=logging.handlers.SysLogHandler.LOG_DAEMON,
            address = '/dev/log'
            )
        sh.setLevel(own_loglevel)
        formatter = logging.Formatter('%(message)s')
        sh.setFormatter(formatter)
        logger.addHandler(sh)

        pidfile = daemon.pidfile.PIDLockFile(pidfullpath)
        context = daemon.DaemonContext(
            umask=0o002,
            pidfile=pidfile,
            detach_process=True
            )
        context.signal_map = {
            signal.SIGTERM: program_cleanup,
            signal.SIGHUP: 'terminate',
            signal.SIGUSR1: reload_program_config,
            }
        if not args.logfile is None:
            context.files_preserve.append(fh.stream)
        # This is when we fork.
        print("***  "+scriptname+" forking to background. ***")
        with context:
            main()
