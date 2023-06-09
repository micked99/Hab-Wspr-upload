#!/usr/bin/python
# Oh wait, you'll usually be running this on Windows :-)
#
# Sondemonitor to APRS bridge
# Copyright (C) 2014 Mark Jessop <vk5qi@rfhead.net>

# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation; either version 2 of the License, or
# (at your option) any later version.

# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.

# You should have received a copy of the GNU General Public License along
# with this program; if not, write to the Free Software Foundation, Inc.,
# 51 Franklin Street, Fifth Floor, Boston, MA 02110-1301 USA.

import configparser
import time, datetime, urllib3, sys
from datetime import timezone
from socket import gethostbyname, gaierror

# from pykml import parser
from socket import *

# transfer the parameters for the telemetrie only once
only_once = 1

config = configparser.ConfigParser()
config.read('balloon.ini')
aprsUser = config['main']['aprsUser']
aprsPass = config['main']['aprsPass']
callsign = config['main']['aprsCallsign']
telemetrie_datas = config['main']['aprs_send_telemetrie_datas']

#Change these to your prefered server if you wish
serverHost = 'rotate.aprs2.net'
serverPort = 14580

update_rate = 30 # Update rate, in seconds.

# Get KML from SondeMonitor and parse into a Python dictionary
def get_sonde():
	sonde_data = {}

	sonde_data["lat"] = str(sys.argv[2])
	sonde_data["lon"] = str(sys.argv[3])
	sonde_data["speed"] = str(sys.argv[4])
	sonde_data["alt"] = "10000"
	sonde_data["id"] = str(sys.argv[1])
	sonde_data["gps"] = str(sys.argv[6])
	sonde_data["sats"] = str(sys.argv[7])
	sonde_data["temp"] = str(sys.argv[8])

	return sonde_data

# Push a Radiosonde data packet to APRS as an object.
def push_balloon_to_aprs(sonde_data):

	global only_once
	global telemetrie_datas
	
	# Pad or limit the sonde ID to 9 characters.
	object_name = sonde_data["id"]
	if len(object_name) > 9:
		object_name = object_name[:9]
	elif len(object_name) < 9:
		object_name = object_name + " "*(9-len(object_name))
	
	# Convert float latitude to APRS format (DDMM.MM)
	lat = float(sonde_data["lat"])
	lat_degree = abs(int(lat))
	lat_minute = abs(lat - int(lat)) * 60.0
	lat_min_str = ("%02.2f" % lat_minute).zfill(5)
	lat_dir = "S"
	if lat>0.0:
		lat_dir = "N"
	lat_str = "%02d%s" % (lat_degree,lat_min_str) + lat_dir
	
	# Convert float longitude to APRS format (DDDMM.MM)
	lon = float(sonde_data["lon"])
	lon_degree = abs(int(lon))
	lon_minute = abs(lon - int(lon)) * 60.0
	lon_min_str = ("%02.2f" % lon_minute).zfill(5)
	lon_dir = "E"
	if lon<0.0:
		lon_dir = "W"
	lon_str = "%03d%s" % (lon_degree,lon_min_str) + lon_dir
	
	# Speed
	speed = sonde_data["speed"]
	
	# Convert Alt (in metres) to feet
	alt = int(float(sonde_data["alt"])/0.3048)
	
	# GPS
	gps = int(float(sonde_data["gps"]))
	
	# Satellites
	sats = int(float(sonde_data["sats"]))
	
	# Temperature
	temp = int(float(sonde_data["temp"]))
	
    # Actual time for current tx number
	counter = datetime.datetime.now(timezone.utc)
	counter = float(counter.strftime("%H%M%S"))
	counter = counter * 0.00381422
	counter = int(counter)

	# Sonde ID must have 9 characters!
	identity = object_name
	print("Identity: ", identity)

	# Produce the APRS object string.
	#  GPS=%01d Sats=%01d Balloon
#	out_str = ";%s*111111z%s/%sO000/%03d/A=%06d Balloon GPS:%01d Sats:%01d" % (object_name,lat_str,lon_str,speed,alt,gps,sats)
	out_str = ";%s*111111z%s/%sO000/%03d/A=%06d DegC:%d GPS:%d Sats:%d Balloon" % (object_name,lat_str,lon_str,speed,alt,temp,gps,sats)

	# create parameter datas
	if only_once == 1 and telemetrie_datas == "1":
		out_str1 = ":%s:PARM.Temp,GPS,Sats" % (identity)
		out_str2 = ":%s:UNIT.DegC,GPS,Sats" % (identity)
		out_str3 = ":%s:EQNS.0,1,0,0,1,0,0,1,0" % (identity)
	
	# create parameter value datas
	if telemetrie_datas == "1":
		out_str4 = "T#%03d,%03d,%03d,%03d" % (counter,temp,gps,sats)

	# Connect to an APRS-IS server, login, then push our object position in.

	try:
		# create socket & connect to server
		sSock = socket(AF_INET, SOCK_STREAM)
		sSock.connect((serverHost, serverPort))
		# logon
		sSock.send(b'user %s pass %s vers VK5QI-Python 0.01\n' % (aprsUser.encode('utf-8'), aprsPass.encode('utf-8')) )
		# send packet
		sSock.send(b'%s>APRS:%s\n' % (callsign.encode('utf-8'), out_str.encode('utf-8')) )
	except socket.gaierror as e:
		print("ERROR",e)
	
	# send parameter datas
	if only_once == 1 and telemetrie_datas == "1":
		time.sleep(2)
		sSock.send(b'%s>APRS:%s\n' % (identity.encode('utf-8'), out_str1.encode('utf-8')) )
		time.sleep(2)
		print_string1 = '%s>APRS:%s' % (identity.encode('utf-8'), out_str1.encode('utf-8'))
		print("String1: ", print_string1)
		sSock.send(b'%s>APRS:%s\n' % (identity.encode('utf-8'), out_str2.encode('utf-8')) )
		time.sleep(2)
		print_string2 = '%s>APRS:%s' % (identity.encode('utf-8'), out_str2.encode('utf-8'))
		print("String2: ", print_string2)
		sSock.send(b'%s>APRS:%s\n' % (identity.encode('utf-8'), out_str3.encode('utf-8')) )
		time.sleep(2)
		print_string3 = '%s>APRS:%s' % (identity.encode('utf-8'), out_str3.encode('utf-8'))
		print("String3: ", print_string3)
		only_once = 0

	# send parameter value datas
	if telemetrie_datas == "1":
		sSock.send(b'%s>APRS:%s\n' % (identity.encode('utf-8'), out_str4.encode('utf-8')) )
		print_string4 = '%s>APRS:%s' % (identity.encode('utf-8'), out_str4.encode('utf-8'))
		print("String4: ", print_string4)
	
	# close socket
	sSock.shutdown(0)
	sSock.close()
	print("Only once: ", only_once)
	print("Telemetrie_var: ", telemetrie_datas)

# EQNS Definition (every value has 3 digits), example 0,0.1,900, Digit1: multiply with 0, Digit2: multiply with 0.1 because of comma, Digit3: add 900 

# VE3OCL-11:PARM.Speed,Temp,Vbat,GPS,Sats
# VE3OCL-11:UNIT.kn,C,V,,
# VE3OCL-11:BITS.11111111,10mW research balloon
# VE3OCL-11:EQNS.0,0.1,0,0,0.1,-273.2,0,0.001,0,0,1,0,0,1,0

# $speed = int(($speed * 10) + 0.5);
# $temp = int((($temp + 273.2) * 10) + 0.5);
# $vbat = int(($vbat * 1000) + 0.5);
	




# For explanation of encoding see:
# http://he.fi/doc/aprs-base91-comment-telemetry.txt


# sub usage ()
# {
#         print STDERR "\n";
#         print STDERR "telem-data91.pl - Format data into compressed base 91 telemetry.\n";
#         print STDERR "\n";
#         print STDERR "Usage:  telem-data91.pl  sequence value1 [ value2 ... ]\n";
#         print STDERR "\n";
#         print STDERR "A sequence number and up to 5 analog values can be specified.\n";
#         print STDERR "Any sixth value must be 8 binary digits.\n";
#         print STDERR "Values must be integers in range of 0 to 8280.\n";


# if ($#ARGV+1 < 2 || $#ARGV+1 > 7) {
#         print STDERR "2 to 7 command line arguments must be provided.\n";
#         usage();
# }


# if ($#ARGV+1 == 7) {
#         if ( ! ($ARGV[6] =~ m/^[01]{8}$/)) {
#                 print STDERR "The sixth value must be 8 binary digits.\n";
#                 usage();
#         }
#         # Convert binary digits to value.
#         $ARGV[6] = oct("0b" . reverse($ARGV[6]));
# }

# $result = "|";

# for ($n = 0 ; $n <= $#ARGV; $n++) {
#         #print $n . " = " . $ARGV[$n] . "\n";
#         $v = $ARGV[$n];
#         if ($v != int($v) || $v < 0 || $v > 8280) {
#                 print STDERR "argn $n - $v is not an integer in range of 0 to 8280.\n";
#                 usage();
#         }

#         $result .= base91($v);
# }

# $result .= "|";
# print "$result\n";
# exit 0;


# sub base91 ()
# {
#         my $x = @_[0];

#         my $d1 = int ($x / 91);
#         my $d2 = $x % 91;

#         return chr($d1+33) . chr($d2+33);
# }
# :

# Py2 & Py3 compability
# import sys
# if sys.version_info[0] >= 3:
#     is_py3 = True
#     string_type = (str, )
#     string_type_parse = string_type + (bytes, )
#     int_type = int
