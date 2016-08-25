# -*- coding: utf-8 -*- 

"""
bot.py
A Twitter bot using the separate letters module to ask for user input
on Twitter to randomize a letter template.

This script is set up to make 4 runs per template. On runs 1-3 it checks
if new input has been tweeted since last run. On 4th run it will read
all missing input from a database (if any), process the current template
and tweet a link to it.

This script is only responsible for the Twitter interaction. The actual
template processing is handled via the letters module while file upoading
to server is done by a separate ftp shell script.

Requirements:
  * As with letters.py, this script relies on the nltk module to tag user 
	input to word classes in order to not mix different classes.
	http://www.nltk.org/
  * Twython for interacting with Twitter.
	https://github.com/ryanmcgrath/twython 
  * Access tokens to Twitter API.
	https://dev.twitter.com/oauth/overview/application-owner-access-tokens

File structure:
  * This script uses one json file for internal bookkeeping:
    bot_data.json - current state of the bot, a dict of:
	 * run_order (list): list of files to process
	 * run (int): the run number the bot is currently.
	   (runs 1,2,3 = ask for input,
	   4 = check final input and tweet result)
	 * current_title (string): the title of the letter currently being 
	   processed
	 * latest_tweet (string): id of the latest tweet
	 * processed (boolean): whether the current template is already processed
  * Additionally Twitter access tokens are read from keys.json. Note that
	this file is empty and the actual tokens needs to inserted before
	the script will run! 

Change log
23.7.2016
  * Small code cleanup to accomadete changes in letters.py
  * moved get_template_status() to letters.py as it's not directly related
	to the bot
9.7.2016
  * Added support for parsing input from the server
	(lajanki.mbnet.fi/active.php): parse_input() now gathers user input
	from Twitter and the server passing it to letter.parse_input() for
	actually adding them to template.pkl
27.5.2016
  * File I/O changed to conform to the changes in letters.py
13.2.2016
  * Initial release
"""

import nltk
import json
import twython
import pprint
import itertools
import glob
import random
import argparse
import sys
import requests
import os.path

import letters

#==================================================================================
# Global consants =
#==================

rpi_path = "/home/pi/python/letters/"
# read required Twitter keys from file
with open(rpi_path+"keys.json") as f:
  KEYS = json.load(f)

API_KEY = KEYS["API_KEY"]
API_SECRET = KEYS["API_SECRET"]
OAUTH_TOKEN = KEYS["OAUTH_TOKEN"]
OAUTH_SECRET = KEYS["OAUTH_SECRET"]

twitter = twython.Twython(API_KEY, API_SECRET, OAUTH_TOKEN, OAUTH_SECRET)
CHECKS_PER_LETTER = 4  # max number of times to ask for user input before processing current letter
CRON_DELTA = 6  # hours between calls to this script in Cron
PATH_TO_SERVER = "http://lajanki.mbnet.fi/active.php"


#==================================================================================
# Input parsing =
#================
def parse_input(parent_id, query="@vocal_applicant"):
  """Reads input from Twitter and website to shuffled list and parse content for input.
  Modifies template.json via letters.parse_input()
  Args:
    parent_id (string): a tweet id string
    query (string): a Twitter search query to be passed to twython object
  """
  input_ = []
  # read input from Twitter
  results = twitter.cursor(twitter.search, q=query, since_id=parent_id, lang="en")
  #results = itertools.islice(results, 7)
  try:
    for res in results:
      user = res["user"]["screen_name"]
      # skip retweets and self tweets
      if "retweeted_status" in res or user == "vocal_applicant":
        continue

      text = res["text"]
      tokens = nltk.word_tokenize(text)
      print "tweet:\n", text
      print user
      input_.append(text)

  # read as many tweets as possible and move on 
  except twython.TwythonRateLimitError as e:
    print e
  except twython.TwythonError as e:
    print e
     
  try:
    # add input from server
    r = requests.get("http://lajanki.mbnet.fi/user_input.json")
    if r.status_code == requests.codes.ok:
      json_ = json.loads(r.text)
      print "Server input:"
      pprint.pprint(json_)
      input_.extend(json_["entry"])
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

  # shuffle and parse the results
  random.shuffle(input_)
  for item in input_:
    letters.parse_input(item)


#==================================================================================
# Bot Initialization =
#=====================
def init_bot():
  """Read contents of ./templates to create a run order, initialize bot status as dict
  and pass it to init_template() to initialize the next template.
  """
  files = glob.glob(rpi_path+"templates/*.txt")
  random.shuffle(files)
  bot_data = {"run_order": files, "run": 1, "current_title": None, "latest_tweet": None, "processed": False}
  init_template(bot_data)


def init_template(bot_data):
  """Select the next template from file to be processed or call init_bot()
  to re-initialize the whole bot.
  Arg:
    bot_data (dict): the bot's current status (see init_bot() above)
  """
  try:
    run_order = bot_data["run_order"]
    bot_data["processed"] = False
    next_ = run_order.pop()
    print "Next template:", next_
    title = letters.parse_letter(next_, 0.35)

    # tweet title and status of the next template
    msg = "Tweet me single words to include in a letter.\nCurrently writing " + title + "."
    if len(msg) > 140:
      msg = "Currently writing " + title
    tweet(msg)
    print "tweet:", msg

    # post status in another tweet
    status = letters.get_template_status()
    tweet_id = tweet(status)
    print "tweet:", status

    # write bot_data to file
    bot_data["run"] = 1
    bot_data["run_order"] = run_order
    bot_data["current_title"] = title
    bot_data["latest_tweet"] = tweet_id

    with open(rpi_path+"bot_status.json", "wb") as f:
      json.dump(bot_data, f)

  # nothing to pop => re-initialize the bot
  except IndexError:
    print "Stack empty, re-initializing..."
    init_bot()
    sys.exit()


#==================================================================================
# Helper functions =
#===================
def tweet(msg):
  """A wrapper around Twython's update_status():
  tweets msg and return its id string.
  Arg:
    msg (string): the message to tweet
  Return
    tweet id
  """
  tweet = twitter.update_status(status=msg)
  tweet_id = tweet["id_str"]
  return tweet_id


#==================================================================================
# Main =
#=======

# Depending on the bot's current state (ie. "pass" number) eiher:
#   1 check for input tweeted since last update, or
#   2 process the current template and tweet a link to result
def main(args):
  # parse command line args passed to main

  # read ./templates to create a run order and store it to file
  # and use the letters module to initialize the next template via init_bot()
  if args.init:
    print "Initializing templates."
    #tweet("Resetting")
    init_bot()

  # show bot status
  elif args.show:
    with open(rpi_path+"bot_status.json", "rb") as f:
      bot_data = json.load(f)
    print "Current title:", bot_data["current_title"]
    print "Processed:", bot_data["processed"]
    print "Run#", bot_data["run"]
    print "Templates left:", len(bot_data["run_order"])
    print "Templates:"
    pprint.pprint(map(os.path.basename, bot_data["run_order"]))

  # No cammand line argument: determine the correct procedure from the bot's current state.
  # Read input and process current template if this is the final call.
  else:
    with open(rpi_path+"bot_status.json", "rb") as f:
      bot_data = json.load(f)

    #with open(rpi_path+"template.pkl", "rb") as template_file:
    #  template_data = pickle.load(template_file) 

    run = bot_data["run"]
    next_run = (run % CHECKS_PER_LETTER) + 1
    print "run:", run

    # final call: process current template and initialize the next one
    if run == CHECKS_PER_LETTER:

      # if current template already processed, initialize the next template and exit
      if bot_data["processed"]:
        init_template(bot_data)
        sys.exit()

      # read the last words from Twitter/server and if necessary, fill missing from database
      print "Final pass"
      parse_input(bot_data["latest_tweet"], "@vocal_applicant")
      letters.fill_missing()

      print "Processing current template. See the generated .txt file for results."
      letters.compose_letter()

      # tweet link to finished letter
      title = bot_data["current_title"]
      link = PATH_TO_SERVER   # path to active.php
      msg = title + ": " + link+"\nCheck " + str(run) +" of " + str(CHECKS_PER_LETTER)
      tweet(msg)  # no need to store tweet id

      # initialize the next template
      init_template(bot_data)
      sys.exit()

    # not the last pass, but current template is already processed: do nothing
    elif bot_data["processed"]:
      print "Waiting for permission to start the next template."

    # not the last pass and current template not yet processed
    else:
      # read input since last call and check if more still needed
      print "Need more words"
      parse_input(bot_data["latest_tweet"], "@vocal_applicant")
      status = letters.get_template_status()

      if status:
        title = bot_data["current_title"]
        msg = "Currently writing " + title + ".\n" + status + "Check " + str(run) +" of " + str(CHECKS_PER_LETTER)
        if len(msg) > 140:
          msg = (status + "\nPass " + str(run) +" of " + str(CHECKS_PER_LETTER))[:140]
        tweet_id = tweet(msg)
        bot_data["latest_tweet"] = tweet_id
        print "tweet:", msg

      # no more words needed: tweet link and mark current template as processed
      else:
        bot_data["processed"] = True
        print "Processing current template. See the generated .txt file for results."
        fname = letters.compose_letter()
        title = bot_data["current_title"]
        link = PATH_TO_SERVER
        msg = title + ": " + link +"\nNext letter in " + str((CHECKS_PER_LETTER - run)*CRON_DELTA) + " hours."

        if len(msg) > 140:
          msg = title + ": " + link
          
        tweet(msg)  # no need to store tweet id


    bot_data["run"] = next_run

    # store bot data as json for PHP compatibility
    with open(rpi_path+"bot_status.json", "wb") as f:
      json.dump(bot_data, f)




if __name__ == "__main__":
  parser = argparse.ArgumentParser(description="Twitter letter randomizer.")
  parser.add_argument("--init", help="Generate a random run order from ./templates", action="store_true")
  parser.add_argument("--show", help="Shows contents of bot_status.json", action="store_true")
  args = parser.parse_args()

  main(args)







