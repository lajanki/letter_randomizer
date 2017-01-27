# -*- coding: utf-8 -*- 

"""
twitterbot.py
Generates randomized letters using letters.py, uploads them to lajanki.mbnet.fi/letters/
and tweets a links to them.


Change log
27.1.2017
 * Minor changes to reflect rewrites in letters.py, Mainly datafiles
   are now stored in the bot-data folder.
25.1.2017
 * Initial version
"""

import json
import twython
import pprint
import glob
import random
import argparse
import sys
import requests
import ftplib
import os
import logging

import letters

#==================================================================================
# Global constants =
#==================

# Create a LetterRandomizer with working directory in bot-data 
letter_randomizer = letters.LetterRandomizer("/home/pi/python/letters/", "bot-data/")
path = letter_randomizer.base  # path to the base folder /home/pi/python/letters/
bot_path = letter_randomizer.wd  # path to bot related files: keys.json, bot_status.json and those created by letter_randomizer

with open(bot_path + "keys.json") as f:
  KEYS = json.load(f)

API_KEY = KEYS["API_KEY"]
API_SECRET = KEYS["API_SECRET"]
OAUTH_TOKEN = KEYS["OAUTH_TOKEN"]
OAUTH_SECRET = KEYS["OAUTH_SECRET"]
FTP_PASSWD = KEYS["FTP_PASSWD"]

twitter = twython.Twython(API_KEY, API_SECRET, OAUTH_TOKEN, OAUTH_SECRET)

# Setup a logger
logging.basicConfig(filename=path + "letters.log", format="%(asctime)s %(message)s", level=logging.INFO)


#==================================================================================
# Input parsing =
#================
def parse_server_input():
  """Read any user input entered through the input field at lajanki.mbnet.fi/letters/active.php and
  parse it for valid words to enter to the current letter template.
  """
  try:
    input_ = []
    r = requests.get("http://lajanki.mbnet.fi/user_input.json")
    if r.status_code == requests.codes.ok:
      res = json.loads(r.text)
      print "Server input:"
      pprint.pprint(res)
      input_.extend(res["entry"])
    elif r.status_code == requests.codes.not_found:
      print "user_input.json is empty"
    else:
      print "Something went wrong when fetching remote user input. The following response was received:"
      print r.text
  except requests.ConnectionError as e:
    print "Could not connect to server"
    print e
  except requests.RequestException as e:
    print "Something went wrong when requesting user_input.json"
    print e

  if input_:
    logging.info("Received {} submissions from server.".format(len(input_)))
    # Shuffle and fill the template
    random.shuffle(input_)
    for item in input_:
      letter_randomizer.parse_input(item)


#==================================================================================
# Bot Initialization =
#=====================
def init_bot():
  """Create a dynamic index of letter templates to randomize and initialize the first template.
  Return:
    the title of the first letter in the index
  """
  files = glob.glob(path + "templates/*.txt")
  random.shuffle(files)

  bot_status = {}
  bot_status["run_order"] = files

  # Parse the letter to a template.json file.
  init_template(bot_status)
  logging.info("Initialized the bot.")
  


def init_template(bot_status):
  """Process a template file by fetching any user input from the server and
  filling missing words from the database. Uploads the result to the server
  and tweets a link to it.
  Arg:
    bot_status (dict): the current status of the bot, a dict of {run_order, current_title}
  """ 
  template = bot_status["run_order"].pop()
  title = letter_randomizer.parse_letter(template) # generates a template.json for this letter 
  bot_status["current_title"] = title

  # Write bot_status to file.
  with open(bot_path + "bot_status.json", "w") as f:
    json.dump(bot_status, f)




#==================================================================================
# Helper functions =
#===================
def tweet():
  """Fill current template with user input from the server and database words,
  upload the file to the server and tweet a link to it.
  Arg:
    msg (string): the message to tweet
  Return
    tweet id
  """
  # Get the title of the current template
  with open(bot_path + "bot_status.json") as f:
    bot_status = json.load(f)
    title = bot_status["current_title"] 

  parse_server_input()
  letter_randomizer.fill_missing()
  letter_path = letter_randomizer.compose_letter()

  # Upload the file to the server
  ftp = ftplib.FTP("lajanki.mbnet.fi", "lajanki", FTP_PASSWD)
  ftp.cwd("/public_html/letters/letters")

  with open(letter_path) as f:
    fname = os.path.basename(letter_path)
    logging.info("Uploading {} to lajanki.mbnet.fi/letters/letters".format(fname))
    ftp.storlines("STOR " + fname, f)

  ftp.cwd("/public_html/letters")
  # Delete user input file from server (the server will create new when needed),
  # or ignore if it doesn't exist
  try:
    ftp.delete("user_input.json")
  except ftplib.error_perm:
    pass

  # Delete local letter file
  os.remove(letter_path)

  # Tweet
  msg = title + "\n" + "http://lajanki.mbnet.fi/letters/active.php"
  logging.info("Tweet: " + msg)
  twitter.update_status(status = msg)

  # Initialize the next template.
  if not bot_status["run_order"]:
    init_bot()

  else:
    init_template(bot_status)

  # Send bot_status.json to the server in order to know the title of the next
  # letter.
  with open(bot_path + "bot_status.json") as f:
    ftp.storlines("STOR bot_status.json", f)
    ftp.quit()




if __name__ == "__main__":
  parser = argparse.ArgumentParser(description="Twitter letter randomizer.")
  parser.add_argument("--init", help="Initialize the bot by generate a random run order from template files.", action="store_true")
  parser.add_argument("--tweet", help="Process current template and tweet it.", action="store_true")
  args = parser.parse_args()

  
  if not os.path.isfile(bot_path + "bot_status.json"):
    print "ERROR: bot_status.json not found: initialize the bot with --init"
    sys.exit()

  if args.init:
    init_bot()

  elif args.tweet:
    tweet()




