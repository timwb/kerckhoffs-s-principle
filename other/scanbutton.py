#!/usr/bin/python3 -u
# -*- coding: utf-8 -*-
import sys, os, daemon, daemon.pidfile, signal, argparse, logging, logging.handlers
import evdev, os.path, sys, subprocess, time

#setup reasonable defaults
scriptname = os.path.splitext(os.path.basename(__file__))[0]
pidfullpath = '/var/run/'+scriptname+'.pid'
keypad = '/dev/input/by-id/usb-13ba_0001-event-kbd'

# 1 (adfsimplex), 2 (adfduplex), 3 (flatbed)
source = '0'
# 1 (color), 2 (grayscale)
color =  '0'
# 1 (text with OCR), 2 (text with orientation detection and OCR), 3 (graphics), 4 (fax, no OCR)
output = '0'
# pdf, tiff, png, jpg (applicable to graphics mode only)
format = 'unset'

def program_cleanup():
    logger.debug("cleanup")
    # close file handles, print stuff to log

def terminate():
    logger.debug("term")

def reload_program_config():
    logger.debug("config")
    # i think this is sigusr 1

def setup():
    if not os.path.islink(keypad):
        logger.critical("CRITICAL: keypad not found, quitting")
        sys.exit('CRITICAL: keypad not found, quitting')


def runcmd(cmd):
    p = subprocess.Popen(cmd, shell=True, stderr=subprocess.PIPE)
    while True:
        out = p.stderr.read(1)
        if (out == '' and p.poll() != None) or type(out) is not str:
            break
        if out != '' and type(out) is str:
            sys.stdout.write(out)
            sys.stdout.flush()

def scan():
    if source == '0' or color == '0' or output == '0' or format == 'unset':
        return
    logger.debug( 'Scanning, source' + source + ', output: ' + output + ', color: ' + color + ', format: ' + format )
    cmd = 'scan.sh -s ' + source + ' -t ' + output + ' -m ' + color + ' -o ' + format
    runcmd(cmd)

def merge():
    logger.debug("Merge!")
    cmd = 'scan.sh -a'
    runcmd(cmd)

def read_kbdevents(dev):
    global source
    global color
    global output
    global format
    for event in dev.read_loop():
        if event.type == 1 and event.value == 0: #key unpress
            if   event.code == evdev.ecodes.ecodes['KEY_KPENTER'] and time.time() - event.timestamp() < 0.01:
                scan()
            elif event.code == evdev.ecodes.ecodes['KEY_BACKSPACE']:
                source = '0'
                color  = '0'
                output = '0'
                format = 'unset'
            elif event.code == evdev.ecodes.ecodes['KEY_KPSLASH']:
                source = '3'
            elif event.code == evdev.ecodes.ecodes['KEY_KPASTERISK']:
                source = '1'
            elif event.code == evdev.ecodes.ecodes['KEY_KPMINUS']:
                source = '2'
            elif event.code == evdev.ecodes.ecodes['KEY_KP7']:
                output = '1'
                format = 'pdf'
            elif event.code == evdev.ecodes.ecodes['KEY_KP8']:
                output = '4'
                format = 'pdf'
            elif event.code == evdev.ecodes.ecodes['KEY_KP9']:
                output = '3'
                format = 'png'
#            elif event.code == evdev.ecodes.ecodes['KEY_KPPLUS']:
#                var = 'something'
            elif event.code == evdev.ecodes.ecodes['KEY_KP4']:
                color = '2'
            elif event.code == evdev.ecodes.ecodes['KEY_KP5']:
                color = '1'
#            elif event.code == evdev.ecodes.ecodes['KEY_KP6']:
#                var = 'something'
            elif event.code == evdev.ecodes.ecodes['KEY_KP1']:
                output = '3'
            elif event.code == evdev.ecodes.ecodes['KEY_KP2']:
                output = '1'
            elif event.code == evdev.ecodes.ecodes['KEY_KP3']:
                output = '2'
            elif event.code == evdev.ecodes.ecodes['KEY_KPDOT'] and time.time() - event.timestamp() < 0.01:
                merge()

def main():
    logger.info(scriptname+" arrived at main()")
    dev = evdev.InputDevice(keypad)
    try:
        dev.grab()
        logger.debug(scriptname+" successfully grabbed device")
    except IOError:
        logger.critical("CRITICAL: keypad already in use, quitting")
        sys.exit('CRITICAL: keypad already in use, quitting')
    read_kbdevents(dev)

if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('-f', '--foreground',        help="Do not daemonize, log to stdout", action='store_true')
    parser.add_argument('-k', '--keypad',            help="Keypad device to use (default: "+keypad+")")
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

    if not args.keypad is None:
        keypad = args.keypad

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
        setup()
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
            working_directory='/tmp',
            umask=0o002,
            pidfile=pidfile,
            detach_process=True
            )
        context.signal_map = {
            signal.SIGTERM: program_cleanup,
            signal.SIGHUP: terminate,
            signal.SIGUSR1: reload_program_config,
            }
        setup()
        context.files_preserve = list()
        if not args.logfile is None:
            context.files_preserve.append(fh.stream)
        # This is when we fork.
        print("*** "+scriptname+" forking to background. ***")
        with context:
            main()
