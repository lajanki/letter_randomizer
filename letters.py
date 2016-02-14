#!/usr/bin/python
# -*- coding: utf-8 -*-

################################################################################
# letters.py                                                                   #
# Creates randomized letters by reading a letter template from file,           #
# parsing it for words to change and filling in new words from user input.     #
#                                                                              #
# New words are either fetched from database or directly asked from user       #
# until no more is needed. The word fetching is meant to take several          #
# separate runs of this script and words read from each run are stored         #
# to file.                                                                     #
#                                                                              #
# This script uses the nltk module to tokenize the template and to identify    #
# which words should be changed as well as making sure that the right type     #
# of word is used to replace old ones (verbs for verbs etc.).                  #
# http://www.nltk.org/                                                         #
#                                                                              #
# This script is mostly intended as a library module for bot.py, which uses    #
# Twitter as a user input source, but can be run directly to simulate the      #
# template processing.                                                         #
#                                                                              #
# File structure:                                                              #
# * This script uses several Pickle encoded files for internal bookkeeping:    #
# 1 index_data.pkl                                                             #
#   metadata of words needed to fill blanks in stripped template               #
#   list: [ ((word, tag), index) ]                                             #
# 2 input.pkl                                                                  #
#   a dict of (word, index) pairs of words read from Twitter to use as         #
#   fillers and a list of line break positions                                 #
#   dict: { words, newlines }                                                  #
# 3 template.pkl                                                               #
#   a tokenized list of the template and the letter title                      #
#   dict: { title, tokens }                                                    #
#                                                                              #
# * Upon first running the script you need to initialize these files by        #
#   using the --init switch.                                                   #
# * Additionally the script uses:                                              #
#   1 quotes.db                                                                #
#      a database with a table of words grouped by their class.                #
#   2 templates                                                                #
#     folder containing letter templates as .txt files                         #
#   3 template/summary.json                                                    #
#     file matching each letter file name to a title/description               #
#                                                                              #
#                                                                              #
# Lauri Ajanki                                                                 #
# 13.2.2016                                                                    #
################################################################################

import nltk
import codecs
import pickle
import json
import pprint
import random
import argparse
import os
import glob
import time
import sqlite3 as lite


# nltk tags for words valid to change
CLASSES = ["JJ", "JJR", "JJS", "NN", "NNS", "RB", "RBR", "VB", "VBN", "VBD", "VBG"]




#==================================================================================
# Template file I/O =
#====================

def parse_letter(path, fragmentation_degree=0.6):
  # Read a letter from file, parse for words to switch and store
  # switch data to file.
  # Args:
  #   path (string): path to file to read
  #   fragmentation_degree (float): the percentage of words with valid tag to switch
  # Return:
  #   the title of the parsed letter

  valid = []  # list for all valid words to change
  with codecs.open(path, "r", encoding="utf-8") as f: # read content as unicode
    text = f.read()

  # get file description from summary.json
  with open("./templates/summary.json", "r") as summary_file:
    summary = json.load(summary_file)
    fname = os.path.basename(path)
    try:
      title = summary[fname]
    except KeyError as e:  # title not inserted in summary.json
      print e
      title = ""

  tokens = nltk.word_tokenize(text)
  tagged = nltk.pos_tag(tokens)

  # find all words that have valid tags
  for idx, item in enumerate(tagged):
    if item[1] in CLASSES:
      valid.append((item, idx))

  # randomly choose fragmentation_degree% of valid words to change
  nwords = int(fragmentation_degree * len(valid))
  change = random.sample(valid, nwords)
  change.sort(key = lambda x: x[1])  # random.sample returns elements in random order, use the index to sort back to the original order

  # insert ___ in place of word to replace
  indices = [idx for (tagged, idx) in change]
  for i in indices:
    tokens[i] = "___"

  # record paragraph lengths: this many words before linebreak needed
  paragraphs = text.split("\n")
  print "original paragraphs:"
  for p in paragraphs:
    print p

  newlines = [ len(p.split()) for p in paragraphs ]

  # store tags and indices of words to change to file using pickle
  with open("index_data.pkl", "wb") as index_file:
    pickle.dump(change, index_file, 2)

  # store modified tokens to file
  with open("template.pkl", "wb") as template_file:
    d = {"title": title, "template": tokens}
    pickle.dump(d, template_file, 2)

  # store newline data to input.pkl
  with open("input.pkl", "wb") as input_file:
    d = {"words": [], "newlines": newlines}  # init a dictionary to separate words from newlines 
    pickle.dump(d, input_file, 2)

  return title


def randomize_letter():
  # Read letter metadata from input.pkl and fill template.pkl to create a randomized letter.
  # Ouputs result as a .txt file 
  # Return:
  #   the name of the generated file

  with open("input.pkl", "rb") as input_file:
    input_data = pickle.load(input_file)  # dict: { words, newlines}
  
  with open("template.pkl", "rb") as template_file:
    template_data = pickle.load(template_file)
    template = template_data["template"]

  # insert new words
  for word_record in input_data["words"]:  # word_record: (word, index)
    template[word_record[1]] = word_record[0]

  # tokenizing and then joining the tokens back together causes some unnecessary white spacing around punctuation,
  # define replacement rules for trimming these
  replacements = {" ,":",", " .":".", " !":"!", " ?":"?", " :": ":", " ;":";", " )":")", "( ":"(", "$ ":"$", "* ":"*", " @ ":"@"}
  text = " ".join(template)

  # replace
  for old, new in replacements.iteritems():
    text = text.replace(old, new)

  # insert linebreaks
  newlines = input_data["newlines"]
  split = text.split()  # re-split and count words before each linebreak

  start = 0
  end = 0
  text = ""
  try:
    for i in newlines:
      end += i
      if i != 0:
        p = split[start:end]
        p[0] = p[0].capitalize()
        text += " ".join(p) + "\n"
      else:  # empty paragraph, insert another linebreak
        text += "\n"

      start = end
  except IndexError as e:
    print e
    print p

  # add date and title at the beginning
  timestamp = time.strftime("%d.%m.%y")
  title = template_data["title"]
  text = title + "\n" + timestamp + "\n\n" + text + "\n\n" + "Help write the next letter at https://twitter.com/vocal_applicant"
  print text

  # store result to file
  # format filename with letter title and timestamp
  title = title.lower()
  title = title.replace(" ", "_")
  timestamp = timestamp.replace(".", "_")
  fname = title + "_" + timestamp + ".txt"
  with open(fname, "w") as output_file:
    output_file.write(text.encode("utf-8"))

  return fname

#==================================================================================
# Helper functions =
#===================
# Note: the next 3 input reading functions are inteded to simulate
# user input parsing done by bot.py

def fetch_word():
  # Input reading 1:
  # Read contents of index_data.pkl and fetch a
  # corresponding word from database.
  # Return:
  #   None (implicit)

  with open("index_data.pkl", "rb") as index_file:
    index_data = pickle.load(index_file)    # ((word, tag), index)

  # read the current contents of input.pkl (file will be overwritten later)
  with open("input.pkl", "rb") as input_file:
    read = pickle.load(input_file)

  next = index_data.pop()
  
  # fetch word from database
  con = lite.connect("./quotes.db")
  cur = con.cursor()
  with con: 
    cur.execute("SELECT word, class FROM dictionary WHERE class = ? ORDER BY RANDOM() LIMIT 1", (next[0][1],))
    row = cur.fetchone()

  print "New word:", row[0]
  print "Words left to fetch:", len(index_data)

  # write the new word data to input.pkl
  read["words"].append((row[0], next[1]))  # (word, index)
  with open("input.pkl", "wb") as input_file:
    pickle.dump(read, input_file, 2)

  # store the rest of index_data back to file
  with open("index_data.pkl", "wb") as index_file:
    pickle.dump(index_data, index_file, 2)


def fetch_words():
  # Input reading 2
  # Read contents of index_data.pkl and fetch all missing words from database.
  # Return:
  #   None (implicit)

  with open("index_data.pkl", "rb") as index_file:
    index_data = pickle.load(index_file)    # ((word, tag), index)

  # read the current contents of input.pkl (file will be overwritten later)
  with open("input.pkl", "rb") as input_file:
    read = pickle.load(input_file)

  # fetch word from database
  con = lite.connect("./quotes.db")
  cur = con.cursor()
  input_data = []
  with con: 
    while index_data:
      next = index_data.pop()
    
      cur.execute("SELECT word, class FROM dictionary WHERE class = ? ORDER BY RANDOM() LIMIT 1", (next[0][1],))
      row = cur.fetchone()
      input_data.append((row[0], next[1]))   # (word, index)

  # input_data is in reverse order duo to popping index_data
  input_data.reverse()

  # write the new word data to input.pkl
  read["words"].extend(input_data)
  with open("input.pkl", "wb") as input_file:
    pickle.dump(read, input_file, 2)

  # store empty index_data back to file to mark input completion
  with open("index_data.pkl", "wb") as index_file:
    pickle.dump(index_data, index_file, 2)


def parse_input():
  # Input reading 3
  # Ask for direct user input and parse for letter words.
  # Return:
  #   None (implicit)

  with open("index_data.pkl", "rb") as index_file:
    index_data = pickle.load(index_file)    # ((word, tag), index)

  with open("input.pkl", "rb") as input_file:   # # dict: { words: (word, idx), newlines}
    read = pickle.load(input_file)
    words = read["words"]

  data = raw_input(">")
  tokens = nltk.word_tokenize(data)
  tagged = nltk.pos_tag(tokens)

  # check if input words match those needed to fill blanks
  for word, tag in tagged:
    valid = [token for token in index_data if token[0][1] == tag]
    #print word, tag
    #print valid

    if valid:
      new = (word, valid[0][1]) # (word, idx)
      old = valid[0]  # ((word, tag), idx) 

      #remove old from index_data and add new to words
      index_data.remove(old)
      words.append(new)

      print "Adding:", new, "as", old

    
  # write index_data and user input back to file
  with open("index_data.pkl", "wb") as index_file:
    pickle.dump(index_data, index_file, 2)

  read["words"] = words
  with open("input.pkl", "wb") as input_file:
    pickle.dump(read, input_file, 2)


def show_files():
  # Show contents of index_data.pkl and input.pkl.
  # Return:
  #   None (implicit)

  with open("index_data.pkl", "rb") as index_file:
    index_data = pickle.load(index_file)  

  # store newline data to input.pkl
  with open("input.pkl", "rb") as input_file:
    read = pickle.load(input_file)

  print "index_data.pkl"
  pprint.pprint(index_data)

  print "input.pkl"
  pprint.pprint(read)
  

def parse_for_db(path):
  # Parse the contents of the given file or all of ./template for words to store
  # in the dictionary table of the database.
  # Args:
  #   path (string): path to file to parse, or
  #   "all" to mark all files to be parsed
  # Return:
  #   None (implicit)

  # The database contains more word classes than this script uses, parse the file for all valid
  # database classes
  DB_CLASSES = ["JJ", "JJR", "JJS", "NN", "NNS", "RB", "RBR", "VB", "VBN", "VBD", "VBG", "VBP", "VBZ" ]
  con = lite.connect("./quotes.db")
  cur = con.cursor()

  if path == "all":
    files = glob.glob("./templates/*.txt")
  else:
    files = [path]

  print "Processing..."
  with con:
    for f in files:
      print f
      with codecs.open(f, "r", encoding="utf-8") as f:
        text = f.read()

      tokens = nltk.word_tokenize(text)
      tagged = nltk.pos_tag(tokens)

      for word, tag in tagged:
        if tag in DB_CLASSES:

          # check if (word, tag) pair is already in dictionary
          cur.execute("SELECT * FROM dictionary WHERE word = ? AND class = ?", (word, tag))
          row = cur.fetchone()
          if row is None:   
            cur.execute("INSERT INTO dictionary(word, class) VALUES(?, ?)", (word, tag))


    print "Database now holds:"
    # show dictionary size
    cur.execute("SELECT COUNT(*) FROM dictionary")
    size = cur.fetchone()
    print size[0], "words"

    for item in DB_CLASSES:
      cur.execute("SELECT COUNT(word) FROM dictionary WHERE class = ?", (item,))
      size = cur.fetchone()
      print item, size[0]



#==================================================================================
# Main =
#=======
# On each run of main() the script checks whether new words needs to be fetched,
# or if the current file is ready to be processed by randomize_letter(). That is,
# this function is intended to be run several times per letter template.

def main(args):
  # open index_data.pkl to see if more words needs to be read
  with open("index_data.pkl", "rb") as index_file:
    index_data = pickle.load(index_file)

  with open("template.pkl", "rb") as template_file:
    template = pickle.load(template_file)

  with open("input.pkl", "rb") as input_file:
    input_data = pickle.load(input_file)

  # more words to fetch
  if index_data:
    print "Fetching new words"

    if args.fetch_all:
      fetch_words()
    else:
      #fetch_word()
      parse_input()

  # no more words needed, either:
  #  1 current template is fully processed -> choose new, or
  #  2 all input read and template needs to be filled -> call randomize_letter to fill the template
  else:
    if input_data["words"]:
      randomize_letter()
    else:
      # choose a random template
      templates = glob.glob("./templates/*.txt")
      path = random.choice(templates)
      parse_letter(path, 0.6)
  
    

if __name__ == "__main__":
  parser = argparse.ArgumentParser(description="Twitter letter randomizer.")
  parser.add_argument("--init", help="Drop all current working data and process a random template from /templates.", action="store_true")
  parser.add_argument("--fetch-all", help="Fill all missing words from the database.", action="store_true")
  parser.add_argument("--parse", metavar="path", help="Parse a template file for valid words and store to database dictionary.")
  parser.add_argument("--parse-all", help="Parse all files from /templates to dictionary.", action="store_true")
  parser.add_argument("--show", help="Shows contents of input.pkl and index_data.pkl.", action="store_true")
  args = parser.parse_args()

  # initialization: randomly select a new template and call parse_letter() to process it
  if args.init:
    templates = glob.glob("./templates/*.txt")
    path = random.choice(templates)

    print "Initializing template", path
    parse_letter(path, 0.6)

  # parse file for dictionary
  elif args.parse:
    parse_for_db(args.parse)

  elif args.parse_all:
    parse_for_db("all")

  # show contents of cache files
  elif args.show:
    show_files()

  # only run main if none of the maintenance flags were set
  else:
    try:
      main(args)
    except IOError as e:
      print e
      print "Use --init switch to initialize the script."


