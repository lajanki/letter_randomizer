#!/bin/sh

# A launcher script to bot.py.
# Run bot.py to generate a new tweet and
# send a possible output file to a web server using curl

python ./bot.py


# loop over all .txt files
FILES=./*.txt
for f in $FILES
do
	# check if any .txt files actually exist
	# (ie. don't take *.txt as a literal filename)
	if [ -f $f ] 
	then
		echo "uploading $(basename $f)"
		# change these to actual ftp address and user data
		curl -T $f ftp://<ftp-address-to-server> --user <user>:<password>

		# remove local copy
		rm $f
	fi

done




