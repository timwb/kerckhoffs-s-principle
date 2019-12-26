import sys, os, time, datetime
import threading
from influxdb import InfluxDBClient

# InfluxDB
host = "1.2.3.4"
port = 8086 # default port
username = os.uname()[1] # Use hostname as user name
password = ""
database = "sensors"
w1sensors = ("28-1234567890AA", "28-1234567890AB")

client = InfluxDBClient(host=host, port=port, username=username, password=password, database=database)

def doit():
    threading.Timer(10.0, doit).start()

    val = [ "", "" ]
    data = []
    datagood = False
    for n in range(len(w1sensors)):
        with open('/sys/devices/w1_bus_master1/'+w1sensors[n]+'/w1_slave', 'r') as sfh:
            while not datagood:
                val[n] = sfh.read()
                val[n] = val[n].split("\n")[1].split(" ")[9]
                val[n] = float(val[n][2:])/1000
                datagood = val[n] > -20 and val[n] < 85
            data.append("{measurement},host={host},sensor={sensor} value={value} {timestamp}"
                        .format(measurement='temperature',
                                host=username,
                                sensor=w1sensors[n],
                                value=val[n],
                                timestamp=time.time_ns()//1000 ))
        datagood = False

    # Send the data to InfluxDB
    #print(data)
    client.write_points(data, time_precision='u', protocol='line')

doit()
