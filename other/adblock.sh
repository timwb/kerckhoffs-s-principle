#!/bin/bash

# Define variables
CustomLists="/etc/adblock"								#Directory path of blacklist & whitelist
TmpFile="/tmp/adblock.new"
ZoneDataFile="/var/cache/bind/adblock/zones.adblock"
ZoneMasterFile="/var/cache/bind/db.null"

YoyoList=1								#3k		#1 to enable or 0 to disable | Automatically import updated version of the yoyo.org blocklist					http://pgl.yoyo.org/as/serverlist.php?hostformat=bindconfig&showintro=0&mimetype=plaintext
Malwaredomains2=0							#17k		#1 to enable or 0 to disable | Automatically import updated version of the malwaredomains.com blocklist				http://mirror2.malwaredomains.com/files/spywaredomains.zones
RandomLargeList=0							#34k		#1 to enable or 0 to disable | Automatically import a large Github blocklist (last updated  )					https://raw.githubusercontent.com/mat1th/Dns-add-block/master/adresses
PiHoleList=1								#27k		#1 to enable or 0 to disable | Automatically import updated version of the official Pi-Hole blocklist				https://raw.githubusercontent.com/StevenBlack/hosts/master/hosts
											#| This Pi-Hole list includes: a custom list + malwaredomainlist.com + WinHelp2002 + someonewhocares + yoyo.org 		https://github.com/pi-hole/pi-hole/blob/master/adlists.default
Malwaredomains1=1							#17k		#1 to enable or 0 to disable | Automatically import updated version of malwaredomains blocklist					http://mirror1.malwaredomains.com/files/justdomains
sysct1=1								#21k		#1 to enable or 0 to disable | Automatically import updated version of sysct1 blocklist						http://sysctl.org/cameleon/hosts
amazonws1=1								#0k		#1 to enable or 0 to disable | Automatically import updated version of amazonsw blocklist					https://s3.amazonaws.com/lists.disconnect.me/simple_tracking.tx
amazonws2=1								#3k		#1 to enable or 0 to disable | Automatically import updated version of amazonsw blocklist					https://s3.amazonaws.com/lists.disconnect.me/simple_ad.txt
HostsFileNet=0								#48k		#1 to enable or 0 to disable | Automatically import updated version of hosts-file.net blocklist					https://hosts-file.net/ad_servers.txt

# Check if needed dependencies exists
Dependencies="chown date grep mv rm sed wget tr fold head cut"
MissingDep=0
for NeededDep in $Dependencies; do
	if ! hash "$NeededDep" >/dev/null 2>&1; then
		printf "Command not found in PATH: %s\n" "$NeededDep" >&2
		MissingDep=$((MissingDep+1))
	fi
done
if [ $MissingDep -gt 0 ]; then
	printf "Minimum %d commands are missing in PATH, aborting\n" "$MissingDep" >&2
	exit 1
fi

TmpFile="${TmpFile}-"$(cat /dev/urandom | tr -dc 'a-zA-Z0-9' | fold -w 32 | head -n 1)
touch "${TmpFile}"

#================================================================================
#Download and process blacklists
#================================================================================

if [[ "$YoyoList" -eq 1 ]]; then
# Download the "blacklist" from "http://pgl.yoyo.org"
	wget -nv "https://pgl.yoyo.org/as/serverlist.php?hostformat=;showintro=0" -O - | sed -e 's/\r\n/\n/g' | sed -e 's/\r/\n/g' | sed -e '/^$/d' >> ${TmpFile}
fi

if [[ "$Malwaredomains2" -eq 1 ]]; then
	# Download blocklist from malwaredomains.com
	wget -nv "http://mirror2.malwaredomains.com/files/spywaredomains.zones" -O - | sed -e 's/\r\n/\n/g' | sed -e 's/\r/\n/g' | sed -e '/^$/d; /\/\//d' | cut -d'"' -f2 >> ${TmpFile}
fi

if [[ "$RandomLargeList" -eq 1 ]]; then
	# Download random blocklist from github (not updated)
	wget -nv "https://github.com/mat1th/Dns-add-block/blob/master/adresses?raw=true" -O - | sed -e 's/\r\n/\n/g' | sed -e 's/\r/\n/g' | sed -e '/^$/d; /\/\//d' | cut -d'"' -f2 >> ${TmpFile}
fi

if [[ "$PiHoleList" -eq 1 ]]; then
	# Download blocklist from Pi-Hole
	wget -nv "https://raw.githubusercontent.com/StevenBlack/hosts/master/hosts" -O - | sed -e '/^0.0.0.0/!d; s/#.*//; s/ *$//; /^$/d; s/\(.*\)/\L\1/' | cut -d' ' -f2 | grep -v '0.0.0.0' >> ${TmpFile}
fi

if [[ "$Malwaredomains1" -eq 1 ]]; then
	# Download blocklist from malwaredomains.com
	wget -nv "http://mirror1.malwaredomains.com/files/justdomains" -O - | sed -e 's/\r\n/\n/g' | sed -e 's/\r/\n/g' | sed -e '/^$/d; s/\(.*\)/\L\1/' >> ${TmpFile}
fi

if [[ "$sysct1" -eq 1 ]]; then
	# Download blocklist from sysct1.com
	wget -nv "http://sysctl.org/cameleon/hosts" -O - | sed -e 's/\r\n/\n/g' | sed -e 's/\r/\n/g' | sed -e '/^127.0.0.1\t /!d; s/#.*//; s/ *$//; /^$/d; s/\(.*\)/\L\1/' | cut -d' ' -f2 |grep -v '127.0.0.1' >> ${TmpFile}
fi

if [[ "$amazonws1" -eq 1 ]]; then
	# Download blocklist from amazonanews.com
	wget -nv "https://s3.amazonaws.com/lists.disconnect.me/simple_tracking.txt" -O - | sed -e 's/\r\n/\n/g' | sed -e 's/\r/\n/g' | sed -e 's/#.*//; s/ *$//; /^$/d; s/\(.*\)/\L\1/' >> ${TmpFile}
fi

if [[ "$amazonws2" -eq 1 ]]; then
	# Download blocklist from amazonanews.com
	wget -nv "https://s3.amazonaws.com/lists.disconnect.me/simple_ad.txt" -O - | sed -e 's/\r\n/\n/g' | sed -e 's/\r/\n/g' | sed -e 's/#.*//; s/ *$//; /^$/d; s/\(.*\)/\L\1/' >> ${TmpFile}
fi

if [[ "$HostsFileNet" -eq 1 ]]; then
	# Download blocklist from Pi-Hole
	wget -nv "https://hosts-file.net/ad_servers.txt" -O - | sed -e 's/\r\n/\n/g' | sed -e 's/\r/\n/g' | sed -e '/^127.0.0.1\t/!d; s/#.*//; s/ *$//; /^$/d; s/\(.*\)/\L\1/' | cut -f2 |grep -v '127.0.0.1' >> ${TmpFile}
fi

#================================================================================
# Process lists into one .db file
#================================================================================

# Sanitize
cat ${TmpFile} | sed -e '/_/d; s/:.*//; s/\(.*\)/\L\1/' | sort | uniq > "${TmpFile}-2"
mv "${TmpFile}-2" ${TmpFile}

# Add blacklist & dedup
# Add whitelist so it gets removed again in case something is in the whitelist that is not in any blacklist.
cat ${CustomLists}/blacklist.txt ${CustomLists}/whitelist.txt ${TmpFile} | sed -e 's/\r\n/\n/g' | sed -e 's/\r/\n/g' | sed -e 's/#.*//; s/ *$//; /^$/d; s/\(.*\)/\L\1/' | sort | uniq > "${TmpFile}-2"
mv "${TmpFile}-2" ${TmpFile}

# Substract the whitelist & finalize
cat ${CustomLists}/whitelist.txt ${TmpFile} | sed -e 's/\r\n/\n/g' | sed -e 's/\r/\n/g' | sed -e 's/#.*//; s/ *$//; /^$/d; s/\(.*\)/\L\1/' | sort | uniq -u | \
grep -Po '(?=^.{1,254}$)(^(?:(?!\d+\.|-)[a-zA-Z0-9_\-]{1,63}(?<!-)\.)+(?:[a-zA-Z]{2,})$)' | \
sed -e 's/^/zone "/g; s/$/" { type master; notify no; file "\/var\/cache\/bind\/db.null"; };/g' > ${ZoneDataFile}

rm ${TmpFile}

#================================================================================
# Update zone file
#================================================================================

# Rebuild master db.null
rm -f ${ZoneMasterFile}
Now=$(date +"%y%m%d%H%M")
echo '$TTL 86400         ; one day'            >> ${ZoneMasterFile}
echo '@ IN    SOA   ns.null.zone.file. mail.null.zone.file. (' >> ${ZoneMasterFile}
echo '      '${Now}' ; serial number YYYYMMDDNN'               >> ${ZoneMasterFile}
echo '      86400      ; refresh   1 day'      >> ${ZoneMasterFile}
echo '      7200       ; retry   2 hours'      >> ${ZoneMasterFile}
echo '      864000     ; expire   10 days'     >> ${ZoneMasterFile}
echo '      86400 )    ; min ttl   1 day'      >> ${ZoneMasterFile}
echo '      NS   ns.null.zone.file.'           >> ${ZoneMasterFile}
echo '       A   127.0.0.1'                    >> ${ZoneMasterFile}
echo '* IN   A   127.0.0.1'                    >> ${ZoneMasterFile}


#================================================================================
# Reload bind
#================================================================================

named-checkconf && systemctl reload bind9

exit 0
