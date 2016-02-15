# letter_randomizer
Creates randomized letters by reading input from Twitter.

## Description

A Python script that fills letter templates by reading input from Twitter. The script
first reads a filled letter from file, randomly selects words to mark as blanks and
asks for user input on Twitter to fill the blanks. Uses Python's nltk module to keep track of
which type of word should fill which blank.

The script is divided into two modules by functionality:
 * letters.py is in charge of creating and filling the letter template, while
 * bot.py handles Twitter interaction

The bot is set up to perform several input queries per template. Therefore keeping track of what
has already been read is mostly done by storing the bot's current status to files. Additionally, if there isn't
enough user input, missing words will be read from a database.

## Requirements

Python modules:
 * Natural Language Toolkit (nltk):
     http://www.nltk.org/index.html
 * Twython:
     https://twython.readthedocs.org/en/latest/

Keys:
 * You will need to register a Twitter app to get your own Twitter access tokens and developer keys, see https://dev.twitter.com/oauth/overview/application-owner-access-tokens Store these keys to the keys.json file.   


## Usage

The letters module can be run directly to simulate the bots actual behavior.
 1. First, initialize the script with the --init switch. This will choose a random letter from the
 templates folder, randomize the words to be marked as blanks and store this information to file
 2. The next 4 calls (by default) will ask for user input and attempt to fill the blanks.
 3. The 4th call ends with any missing words being read from a database and the template being processed and
 printed on screen. You can also the --fetch-all switch to fetch all missing words from the database at once.
 
To use the bot:
  1. First, fill keys.json with valid Twitter access tokens and set the twitter_account parameter to your account.
  2. Initialize the bot with --init switch.
  3. Subsequent calls to bot.py will then behave much like the letters module above: on calls 1-3 the bot will check
 if it has received any tweets and attempt to fill any blanks. On the 4th call the bot will additionally fill any remaining
 blanks from a database and tweet a link to the processed file.
 
 Note that neither of the Python scripts will actually upload any output anywhere. Running the bot and uploading
 output to a web server is delegated to bot.sh.
 

## File structure

Running either of the Python scripts will create several Pickle encoded metadata files for internal bookkeeping:
 * index_data.pkl
   metadata of words needed to fill blanks in stripped template
   list: [ ((word, tag), index) ]
 * input.pkl
   a dict of 2: a list of (word, index) pairs of words read from Twitter and their numerical indices
   telling where in the template they should be inserted, and a list of line break positions.
   dict: { words, newlines }
 * template.pkl
   a tokenized list of the template and the letter title
   dict: { title, tokens }
 * bot_data.pkl
   current state of the bot, a dict of: 
   * run_order (list): list of files to process
   * run (int): which pass of 4 the bot is currently on
   * current_title (string): current letter title 
   * latest_tweet (string): id of the latest tweet
   * processed (bool): whether the current template is already

Addtionally:
  * the templates folder contains a collection pre-filled letters and summary json file defining
a title for each filename
  * quotes.db is a database containing a dictionary table which contains words and an nltk tag
    telling which word class each word belong, see my quote_randomizer for more detailed description.
  * keys.json is an empty storage space for Twitters access tokens, and
  * bot.sh is a Linux launcher script for running bot.py and for sending any generated output to a web server.




___
Written on Python 2.7.8

Lauri Ajanki 15.2.2016

