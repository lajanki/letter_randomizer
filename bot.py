# -*- coding: utf-8 -*- 

###############################################################################
# bot.py                                                                      #
# A Twitter bot using the separate letters module to ask for user input       #
# on Twitter to randomize a letter template.                                  #
#                                                                             #
# This script is set up to make 4 runs per template. On runs 1-3 it checks    #
# if new input has been tweeted since last run. On 4th run it will read       #
# all missing input from a database (if any), process the current template    #
# and tweet a link to it.                                                     #
#                                                                             #
# This script is only responsible for the Twitter interaction. The actual     #
# template processing is handled via the letters module while file upoading   #
# to server is done by a separate ftp shell script.                           #
#                                                                             #
# Requirements:                                                               #
# * As with letters.py, this script relies on the nltk module to tag user     #
#   input to word classes in order to not mix different classes.              #
#   http://www.nltk.org/                                                      #
# * Twython for interacting with Twitter.                                     #
#   https://github.com/ryanmcgrath/twython                                    #
# * Access tokens to Twitter API.                                             #
#   https://dev.twitter.com/oauth/overview/application-owner-access-tokens    #
#                                                                             #
# File structure:                                                             #
# * This script one Pickle encoded file for internal bookkeeping:             #
#    bot_data.pkl - current state of the bot, a dict of:                      #
#    * run_order (list): list of files to process                             #
#    * run (int): the run number the bot is currently.                        #
#        (runs 1,2,3 = ask for input,                                         #
#	      4 = check final input and tweet result) 							  #
#    * current_title (string): the title of the letter currently being 		  #
#	   processed                        									  #
#    * latest_tweet (string): id of the latest tweet                          #
#    * processed (bool): whether the current template is already processed    #
# * Additionally Twitter access tokens are read from keys.json. Note that     #
#   this file is empty and the actual tokens needs to inserted before         #
#   the script will run!                                                      # 
#                                                                             #
# Change log  															      #
# 27.5.2016 																  #
#	-File I/O changed to conform to the changes in letters.py                 #
# 13.2.2016 																  #
#	-Initial release 														  #
#                                                                             #
# Lauri Ajanki                                                                #
# 14.2.2016                                                                   #
###############################################################################

import nltk
import json
import twython
import pprint
import itertools
import glob
import random
import pickle
import argparse
import sys

import letters



#==================================================================================
# Global consants =
#==================

# read required Twitter keys from file
with open("keys.json") as f:
  KEYS = json.load(f)

API_KEY = KEYS["API_KEY"]
API_SECRET = KEYS["API_SECRET"]
OAUTH_TOKEN = KEYS["OAUTH_TOKEN"]
OAUTH_SECRET = KEYS["OAUTH_SECRET"]

twitter = twython.Twython(API_KEY, API_SECRET, OAUTH_TOKEN, OAUTH_SECRET)
CHECKS_PER_LETTER = 4  # max number of times to ask for user input before processing current letter
CRON_DELTA = 6  # hours between calls to this script in Cron
PATH_TO_SERVER = "http://lajanki.mbnet.fi/active.php"  # link to the server where processed file will be sent



#==================================================================================
# Bot state setting functions =
#==============================
def parse_twitter(parent_id, query="@vocal_applicant", first_only=True):
  """Reads Twitter for tweets posted after parent_id and
  parses them for input to current template.
  Args:
    parent_id (str): a tweet id string
    query (str): a Twitter search query to be passed to twython object
    first_only (boolean): whether only the first valid word of a tweet should be parsed
  """
  with open("template.pkl", "rb") as template_file:
    template_data = pickle.load(template_file)
    change_frame = template_data["change_frame"]
    template = template_data["template"]

  results = twitter.cursor(twitter.search, q=query, since_id=parent_id, lang="en")
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

      # strip unwanted tokens
      stripped = []
      for token in tokens:
        if not any(item in token for item in ["//", "html", "@", "http"]):
          stripped.append(token)
          if first_only:
            break

      print "stripped\n", stripped
      tagged = nltk.pos_tag(stripped)

      # check if tagged words match those needed to fill blanks
      for word, tag in tagged:
        # get change_frame tuples with matching tag
        valid = [token for token in change_frame if token[2] == tag]

        # use the topmost item in valid as directive for the change
        if valid:
          data = valid.pop()
          new = (word, (data[0], data[1])) # (word, (paragraph index, word index))
          old = template[data[0]][0][data[1]]

          # add new word to template and remove old data from change_frame
          print "Adding:", new[0], "as", old
          template[data[0]][0][data[1]] = new[0]
          change_frame.remove(data)

  # read as many tweets as possible and move on 
  except twython.TwythonRateLimitError as e:
    print e
  

  template_data["template"] = template
  template_data["change_frame"] = change_frame
  with open("template.pkl", "wb") as template_file:
    pickle.dump(template_data, template_file, 2)


def init_bot():
  """Read contents of ./templates to create a run order, initialize bot status as dict
  and pass it to init_template() to initialize the next template.
  """
  files = glob.glob("templates/*.txt")
  random.shuffle(files)
  bot_data = {"run_order": files, "run": 1, "current_title": None, "latest_tweet": None, "processed": False}
  init_template(bot_data)


def init_template(bot_data):
  """Select the next template from file to be processed or call init_bot()
  to re-initialize the whole bot.
  Arg:
    bot_data (dict): the bot's current status
  """
  try:
    run_order = bot_data["run_order"]
    bot_data["processed"] = False
    next_ = run_order.pop()
    print "Next template:", next_
    title = letters.parse_letter(next_, 0.6)

    # tweet title and status of the next template
    msg = "Tweet me single words to include in a letter.\nCurrently writing " + title + "."
    if len(msg) > 140:
      msg = "Currently writing " + title
    tweet(msg)
    print "tweet:", msg

    # post status in another tweet
    status = get_template_status()
    tweet_id = tweet(status)
    print "tweet:", status

    # write bot_data to file
    bot_data["run"] = 1
    bot_data["run_order"] = run_order
    bot_data["current_title"] = title
    bot_data["latest_tweet"] = tweet_id
    with open("bot_data.pkl", "wb") as data_file:
      pickle.dump(bot_data, data_file, 2)

  # nothing to pop => re-initialize the bot
  except IndexError:
    init_bot()
    sys.exit()


#==================================================================================
# Helper functions =
#===================
def get_template_status():
  """Check how many words are still needed to fill the current template.
  Return:
    a string describing how many adjectives, nouns, verbs and adverbs are needed
  """
  with open("template.pkl", "rb") as template_file:
    template_data = pickle.load(template_file)
    change_frame = template_data["change_frame"]
    template = template_data["template"]

  # no more words needed, return an empty string
  if not change_frame:
    return ""

  # create a dict to map tags to number of matching words needed
  tags = [token[2] for token in change_frame]
  d = dict.fromkeys(letters.CLASSES, 0)
  for tag in tags:
    d[tag] = tags.count(tag)

  # new dict for printing grouped data
  d_h = dict()
  d_h["adjectives"] = d["JJ"] + d["JJR"] + d["JJS"]
  d_h["nouns"] = d["NN"] + d["NNS"]
  d_h["verbs"] = d["VB"] + d["VBN"] + d["VBD"] + d["VBG"]
  d_h["adverbs"] = d["RB"] + d["RBR"]

  need = "Words needed:\n"
  for key in d_h:
    if d_h[key] > 1:
      need += str(d_h[key]) + " " + key +"\n"
    elif d_h[key] == 1:
      need += str(d_h[key]) + " " + key[:-1] +"\n"
  return need


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
    init_bot()

  # show contents of template.pkl and bot_data.pkl
  elif args.show:
    letters.show_files()
    with open("bot_data.pkl", "rb") as data_file:
      bot_data = pickle.load(data_file)
    pprint.pprint(bot_data)

  # No cammand line argument: determine the correct procedure from the bot's current state.
  # Read input and process current template if this is the final call.
  else:
    with open("bot_data.pkl", "rb") as data_file:
      bot_data = pickle.load(data_file)

    with open("template.pkl", "rb") as template_file:
      template_data = pickle.load(template_file) 


    run = bot_data["run"]
    next_run = (run % CHECKS_PER_LETTER) + 1
    print "run:", run

    # final call: process current template and initialize the next one
    if run == CHECKS_PER_LETTER:

      # if current template already processed, initialize the next template and exit
      if bot_data["processed"]:
        init_template(bot_data)
        sys.exit()

      # read the last words from Twitter and if necessary, fill missing from database
      print "Final pass"
      parse_twitter(bot_data["latest_tweet"], "@vocal_applicant")
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


    # not the last pass and bot not yet processed
    else:
      # read input since last call and check if more still needed
      print "Need more words"
      parse_twitter(bot_data["latest_tweet"], "@vocal_applicant")
      status = get_template_status()

      if status:
        title = bot_data["current_title"]
        msg = "Currently writing " + title + ".\n" + status + "\nCheck " + str(run) +" of " + str(CHECKS_PER_LETTER)
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
    with open("bot_data.pkl", "wb") as data_file:
      pickle.dump(bot_data, data_file, 2)




if __name__ == "__main__":
  parser = argparse.ArgumentParser(description="Twitter letter randomizer.")
  parser.add_argument("--init", help="Generate a random run order from ./templates", action="store_true")
  parser.add_argument("--show", help="Shows contents of input.pkl and index_data.pkl", action="store_true")
  args = parser.parse_args()

  main(args)







