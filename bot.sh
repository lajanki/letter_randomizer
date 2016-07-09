#!/bin/bash

# Shell script for running bot.py:
#  1 run bot.py to generate a new tweet,
#  2 if any input was generated, send to server via curl,
#  3 empty user input submitted through the server
#  4 send bot's current status to server
# 9.7.2016

# store logging output to temp file and append it to the actual log
echo $(date +"%d.%m.%Y %H:%M:%S") > new
python /home/pi/python/letters/bot.py >> new 2>&1

# combine with the old log
cat new /home/pi/letters.log > temp  
mv temp /home/pi/letters.log
rm new

# loop over all .txt files
FILES=/home/pi/python/letters/*.txt
for f in $FILES
do
	# check if any .txt files actually exist
	# (ie. don't take /home/pi/python/letters/*.txt as a literal filename)
	if [ -f $f ] 
	then
		echo "uploading $(basename $f)"
		/usr/bin/curl -T $f ftp://lajanki.mbnet.fi/public_html/letters/ --user lajanki:19ca69d99Hc61c976c8dade9Nb11685

		# remove local copy
		rm $f
	fi
done


# empty user_input.json from server
curl -u lajanki:19ca69d99Hc61c976c8dade9Nb11685 ftp://lajanki.mbnet.fi -Q "DELE public_html/user_input.json"

# send bot_status.json to server
curl -u lajanki:19ca69d99Hc61c976c8dade9Nb11685 -T /home/pi/python/letters/bot_status.json ftp://lajanki.mbnet.fi/public_html/