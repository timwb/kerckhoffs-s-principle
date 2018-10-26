#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import sys, io, signal, time, requests, logging
from datetime import datetime

import RPi.GPIO as GPIO

from picamera import PiCamera

import http.client as http_client
http_client.HTTPConnection.debuglevel = 1

# You must initialize logging, otherwise you'll not see debug output.
logging.basicConfig()
logging.getLogger().setLevel(logging.DEBUG)
requests_log = logging.getLogger("requests.packages.urllib3")
requests_log.setLevel(logging.DEBUG)
requests_log.propagate = True

#Broadcom GPIO numbers
GPIO.setmode(GPIO.BCM)
gpioDeurbel = 17

# Pushover setup
api_url   = 'https://api.pushover.net/1/messages.json'
payload = { 'token':     '',
            'user':      '',
            'message':   '',
            'timestamp': 0.0
          }


GPIO.setup(gpioDeurbel, GPIO.IN, pull_up_down=GPIO.PUD_UP)
deurbeltimeOld = time.time() - 120

def dingdong(channel):
    global deurbeltimeOld
    deurbeltimeNew = time.time()
    # don't ring again if it is within 2 minutes
    if deurbeltimeNew - deurbeltimeOld > 120:
        deurbeltimeOld = deurbeltimeNew
        print(time.asctime())
        print("falling edge detected on 17")
        snap()
    else:
        print(time.asctime())
        print("ignored falling edge on 17")

def signal_handler(signal, frame):
    print('taking snapshot')
    snap2()
    #sys.exit(0)

GPIO.add_event_detect(17, GPIO.FALLING, callback=dingdong, bouncetime=300)

def snap():
    payload['message'] = "Ding dong"
    payload['timestamp'] = time.time()
    print(stream.getbuffer().nbytes)
    r = ses.post(api_url, data=payload, files={"attachment": ("image.jpg", stream.getvalue(), "image/jpeg")} )
    print(r.status_code)
    print(r.headers)
    print(r.json())
    print(r.text)

def snap2():
    payload['message'] = "Test snap from keyboard interrupt"
    payload['timestamp'] = time.time()
    print(stream.getbuffer().nbytes)
    with open('/dev/shm/bla.jpg','wb') as snap:
        snap.write(stream.read())
    ka = time.time()
    with ses.get('https://api.pushover.net/1/apps/limits.json?token=redacted') as lim:
        print("Request took "+str(time.time()-ka))
        foo = lim.text
    #r = ses.post(api_url, data=payload, files={"attachment": ("image.jpg", stream.getvalue(), "image/jpeg")} )
    #print(r.status_code)
    #print(r.headers)
    #print(r.json())
    #print(r.text)

stream = io.BytesIO()
camera = PiCamera()
camera.resolution = (1280, 960)
camera.framerate  = 25
#camera.start_preview()
time.sleep(2)

signal.signal(signal.SIGINT, signal_handler)
#print('Press Ctrl+C')
#while True:
#    time.sleep(60)

ka = time.time()
ses = requests.Session()
with ses.get('https://api.pushover.net/1/apps/limits.json?token=redacted') as lim:
    print("Request took "+str(time.time()-ka))
    foo = lim.text

# Quality 7 is roughly equivalent to JPEG Q 49
for foo in camera.capture_continuous(stream, format='jpeg', use_video_port=False, quality=7, thumbnail=(64, 48, 35)):
    # Truncate the stream to the current position (in case prior iterations output a longer image)
    stream.truncate()
    stream.seek(0)
