#!/usr/bin/env python3

# rpi_rf wrapper to control Renkforce / Conrad 433MHz RC wall sockets
# Remote + 2 Sockets:  p/n 1208454, EAN 4016138910049
# Remote + 1 Socket:   p/n 1208455, EAN 4016138910063
# Socket only:         p/n 1208457, EAN 4016138910087
# IP44 outdoor Socket: p/n 1558920, EAN 4016139196794

import argparse
from rpi_rf import RFDevice

# Telegram consists of address + channel + on/off, 12 bits in total, interleaved with 0's to 24 bits
codes = {
  "address": {
    "I":   0b0111,
    "II":  0b1011,
    "III": 0b1101,
    "IV":  0b1110
  },
  "channel": {
    1:     0b0111,
    2:     0b1011,
    3:     0b1101,
    4:     0b1110
  },
  "onoff": {
    "on":  0b1111,
    "off": 0b1110
  }
}

# interleave each bit with a leading 0, so 0b1111 becomes 0b01010101
def interleavebits(bits):
  bit = ( (0b0001 & bits)      ,
          (0b0010 & bits) >> 1 ,
          (0b0100 & bits) >> 2 ,
          (0b1000 & bits) >> 3
        )
  return bit[3] << 6 | bit[2] << 4 | bit[1] << 2 | bit[0]


parser = argparse.ArgumentParser(description='Control Renkforce / Conrad RC wall sockets')
parser.add_argument('address', metavar='ADDRESS', type=str,
                    help="Which address (I, II, III, IV)")
parser.add_argument('channel', metavar='CHANNEL', type=int,
                    help="Which channel (1, 2, 3, 4)")
parser.add_argument('onoff', metavar='ONOFF', type=str,
                    help="on or off")
parser.add_argument('-g', dest='gpio', type=int, default=17,
                    help="GPIO pin (Default: 17)")
parser.add_argument('-r', dest='repeat', type=int, default=10,
                    help="Repeat cycles (Default: 10)")
args = parser.parse_args()

rfdevice = RFDevice(args.gpio)
rfdevice.enable_tx()
rfdevice.tx_repeat = args.repeat

protocol = 1
pulselength = 426

code = interleavebits(codes['address'][args.address]) << 16 | interleavebits(codes['channel'][args.channel]) << 8 | interleavebits(codes['onoff'][args.onoff])

#print(bin(code))
#print(int(code))

rfdevice.tx_code(code, protocol, pulselength, 24)
rfdevice.cleanup()
