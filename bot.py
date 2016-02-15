#!/usr/bin/python
# -*- coding: utf-8 -*- 

###############################################################################
# bot.py                                                                      #
# A Twitter bot using the separate letters module to ask for user input       #
# on Twitter to randomize a letter template.                                  #
#                                                                             #
# This script is set up to make 4 runs per template. On run 1-3 it checks     #
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
#   1 bot_data.pkl - current state of the bot, a dict of:                     #
#    * run_order (list): list of files to process                             #
#    * run (int): which pass of 4 is the bot currently                        #
#      (passes 1,2,3 = ask for input, 4 = check final input and tweet result) #
#    * current_title (string): current letter title                           #
#    * latest_tweet (string): id of the latest tweet                          #
#    * processed (bool): whether the current template is already              #
# * Additionally Twitter access tokens are read from keys.json. Note that     #
#   this file is empty and the actual tokens needs to inserted before         #
#   the script will run!                                                      # 
#                                                                             #
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
with open("./keys.json") as f:
  KEYS = json.load(f)

API_KEY = KEYS["API_KEY"]
API_SECRET = KEYS["API_SECRET"]
OAUTH_TOKEN = KEYS["OAUTH_TOKEN"]
OAUTH_SECRET = KEYS["OAUTH_SECRET"]

twitter = twython.Twython(API_KEY, API_SECRET, OAUTH_TOKEN, OAUTH_SECRET)
CHECKS_PER_LETTER = 4  # max number of times to ask for user input before processing current template
CRON_DELTA = 6  # hours between calls to this script in Cron: 4 calls 6 hours apart = 1 processed letter in every 24 hours
TWITTER_ACCOUNT = "@vocal_applicant"  # the bot's Twitter account
PATH_TO_SERVER = "http://lajanki.mbnet.fi/letters/" # server to where the bot should link to



#==================================================================================
# Bot state setting functions =
#==============================

def parse_twitter(parent_id, query=TWITTER_ACCOUNT, first_only=True):
  # Queries Twitter for tweets posted after parent_id and
  # parses them for input.pkl.
  # The query parameters are used to find tweets send to the bot (tweets containing "@vocal_applicant")
  # sent after the bot's latest update. 
  # Arg:
  #   parent_id (str): a tweet id string to pass for Twython's search function's since_id parameter
  #   query (str): the search query to pass to Twython
  #   first_only (boolean): whether only the first word of a tweet should be parsed for user input
  # Return:
  #  None (implicit)

  with open("./index_data.pkl", "rb") as index_file:
    index_data = pickle.load(index_file)      # metadata of words still needed from user input. A list of tuples: ((word, tag), index)

  with open("./input.pkl", "rb") as input_file:   # words already read. A dict: { words: (word, idx), newlines}
    read = pickle.load(input_file)
    words = read["words"]

  results = twitter.cursor(twitter.search, q=query, since_id=parent_id)
  try:
    for next in results:
      user = next["user"]["screen_name"]
      # skip retweets and self tweets
      if "retweeted_status" in next or user == "vocal_applicant":
        continue

      text = next["text"]
      tokens = nltk.word_tokenize(text)

      # strip unwanted tokens
      stripped = []
      for token in tokens:
        if not any(item in token for item in ["//", "html", "@", "http"]):
          stripped.append(token)
          if first_only:
            break

        stripped.append(token)

      tagged = nltk.pos_tag(stripped)

      # check if tagged words match those needed to fill blanks
      for word, tag in tagged:
        valid = [token for token in index_data if token[0][1] == tag]

        if valid:
          new = (word, valid[0][1]) # (word, idx)
          old = valid[0]  # ((word, tag), idx) 

          # remove old from index_data and add new to words
          index_data.remove(old)
          words.append(new)

          print "Adding:", new, "as", old

  # read as many tweets as possible and move on 
  except twython.TwythonRateLimitError as e:
    print e
  
  # write index_data and user input back to file
  with open("./index_data.pkl", "wb") as index_file:
    pickle.dump(index_data, index_file, 2)

  read["words"] = words
  with open("./input.pkl", "wb") as input_file:
    pickle.dump(read, input_file, 2)


def init_bot():
  # Read contents of ./templates to create a run order, store it to file
  # and use the letters module to initialize the next template.
  # Return:
  #  None (implicit)

  files = glob.glob("./templates/*.txt")
  random.shuffle(files)
  bot_data = {"run_order": files, "run": 1, "current_title": None, "latest_tweet": None, "processed": False}
  init_template(bot_data)


def init_template(bot_data):
  # Select the next template from file to be processed or call init_bot()
  # to re-initialize the whole bot.
  # Arg:
  #   bot_data (dict): the bot's current status
  # Return:
  #  None (implicit)

  try:
    run_order = bot_data["run_order"]
    bot_data["processed"] = False
    next = run_order.pop()
    print "Next template:", next
    title = letters.parse_letter(next, 0.6)

    # tweet title and status of the next template
    msg = "Tweet me single words to include in a letter.\nCurrently writing " + title + "."
    if len(msg) > 140:
      msg = "Currently writing " + title
    tweet(msg)
    print "tweet:", msg

    # status in another tweet
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
    print "No more templates to proces: re-initializing..."
    init_bot()
    sys.exit()


#==================================================================================
# Helper functions =
#===================

def get_template_status():
  # Check how many words are still needed to fill the current template.
  # Return:
  #   a string describing how many adjectives, nouns, verbs and adverbs are needed

  with open("./index_data.pkl", "rb") as index_file:
    index_data = pickle.load(index_file)  # ((word, tag), index)

  # no more words needed, return an empty string
  if not index_data:
    return ""

  # create a dict to map tags to number of matching words needed
  tags = [token[0][1] for token in index_data]
  d = dict.fromkeys(letters.CLASSES, 0)
  for tag in tags:
    d[tag] = len([token[0][0] for token in index_data if token[0][1] == tag])

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
  # A wrapper around Twython's update_status():
  # tweets msg and returns its id string.
  # Arg:
  #   msg (string): the message to tweet
  # Return
  #   the id of the tweet

  tweet = twitter.update_status(status=msg)
  tweet_id = tweet["id_str"]
  return tweet_id


#==================================================================================
# Main =
#=======

def main(args):
  # Depending on the bot's current state (pass number) eiher:
  #   1 check for user input tweeted since last update, or
  #   2 process the current template and tweet a link to the result
  # Args:
  #  args: the command line arguments parsed by argparse 

  # Initialization: read contents of ./templates to create a run order, store it to file
  # and use the letters module to initialize the next template
  if args.init:
    print "Initializing templates."
    init_bot()

  elif args.show:
    letters.show_files()

  # add new files from ./templates to run order
  elif args.update:
    print "Updating templates."
    with open("./bot_data.pkl", "rb") as data_file:
      data = pickle.load(data_file)
      run_order = data["run_order"]

    # read files from folder
    files = glob.glob("./templates/*.txt")
    run_order.extend([template for template in files if template not in run_order])
    
    # store back to file
    with open("./bot_data.pkl", "wb") as data_file:
      data["run_order"] = run_order
      pickle.dump(data, data_file, 2)

  # Normal execution procedure:
  # read input and process current template if this is the final call
  else:
    with open("./bot_data.pkl", "rb") as data_file:
      bot_data = pickle.load(data_file)

    with open("./index_data.pkl", "rb") as index_file:
      index_data = pickle.load(index_file)  # ((word, tag), index)

    run = bot_data["run"]
    next_run = (run % CHECKS_PER_LETTER) + 1
    print "run:", run

    # case 1: final call. Process current template and initialize the next one
    if run == CHECKS_PER_LETTER:

      # if current template already processed, initialize the next template and exit
      if bot_data["processed"]:
        init_template(bot_data)
        sys.exit()

      # read the last words from Twitter and if necessary, fill missing from database
      print "Final pass"
      #letters.parse_input()
      parse_twitter(bot_data["latest_tweet"], TWITTER_ACCOUNT)
      letters.fetch_words()

      print "Processing current template. See the generated .txt file for results."
      fname = letters.randomize_letter()
      # tweet link to finished letter
      # NOTE: the bot won't actually send the file to the server! This is done by a separete
      # shell script after this script exits
      title = bot_data["current_title"]
      link = PATH_TO_SERVER + fname
      msg = title + ": " + link+"\nCheck " + str(run) +" of " + str(CHECKS_PER_LETTER)
      tweet(msg)  # no need to store tweet id

      # initialize the next template
      init_template(bot_data)
      sys.exit()


    # case 2: not the last pass, but current template is already processed. Wait until
    # the 4th pass to start the next template
    elif bot_data["processed"]:
      print "Waiting for permission to start the next template."


    # case 3: not the last pass and more words to read. Cehck for Twitter input
    else:
      # read input since last call and check if more still needed
      print "Need more words"
      parse_twitter(bot_data["latest_tweet"], TWITTER_ACCOUNT)
      status = get_template_status()

      # check if these were the final words needed
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
        fname = letters.randomize_letter()
        title = bot_data["current_title"]
        link = PATH_TO_SERVER + fname
        msg = title + ": " + fname +"\nNext letter in " + str((CHECKS_PER_LETTER - run)*CRON_DELTA) + " hours."
        tweet(msg)  # no need to store tweet id


    bot_data["run"] = next_run
    with open("./bot_data.pkl", "wb") as data_file:
      pickle.dump(bot_data, data_file, 2)




if __name__ == "__main__":
  parser = argparse.ArgumentParser(description="Twitter letter randomizer.")
  parser.add_argument("--init", help="Generate a random run order from ./templates", action="store_true")
  parser.add_argument("--update", help="Add new files from ./templates to run_order", action="store_true")
  parser.add_argument("--show", help="Shows contents of input.pkl and index_data.pkl", action="store_true")
  args = parser.parse_args()

  try:
    main(args)
  except IOError as e:
    print e
    print "Initialize the bot with the --init switch"





