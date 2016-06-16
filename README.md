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

The bot is set up to perform several input queries per template. The bot's current status as well as the template's current status is stored in Pickle encoded files.

## Requirements

Python modules:
 * Natural Language Toolkit (nltk):
     http://www.nltk.org/index.html
 * Twython:
     https://twython.readthedocs.org/en/latest/

Keys:
 * You will need to register a Twitter app to get your own Twitter access tokens and developer keys, see https://dev.twitter.com/oauth/overview/application-owner-access-tokens Store these keys to the keys.json file.


## Usage

The letters module can be run directly to generate a randomized letter whose missing words are read from a database.
 1. First, initialize the script with the --init switch. This will choose a random letter from the templates folder, randomize the words to be marked as blanks and store this information to file
 2. The next 4 calls (by default) will ask for user input and attempt to fill the blanks.
 3. The 4th call ends with any missing words being read from a database and the template being processed and
 printed on screen. You can also the --fetch-all switch to fetch all missing words from the database at once.
 
To use the bot:
  1. First, fill keys.json with valid Twitter access tokens.
  2. Initialize the bot with --init switch.
  3. Subsequent calls to bot.py will then either parse tweets sent to @vocal_applicant (you probably want to change this) for words to use as input to template or, on the 4th call, fill missing words from database and store the result as a .txt file. The bot will also tweet a link to the file, but it is not responsible for sending the file to the server. The launcher script bot.sh will take care of the uploading.


## File structure

Running either of the Python scripts will create several Pickle encoded metadata files for internal bookkeeping:
 * Template data regarding the position and types of words needed is stored in template.pkl
 * The bot's status is stored in bot_data.pkl, which consists of:
   * run_order (list): list of files to process
   * run (int): the run number the bot is currently on
   * current_title (string): the title of the letter currently being processed
   * latest_tweet (string): id of the latest tweet
   * processed (bool): whether the current template is already processed

Addtionally:
  * the templates folder contains a collection pre-filled letters and summary json file defining a title for each filename
  * quotes.db is a database containing a dictionary table which contains words and an nltk tag telling which word class each word belong, see my quote_randomizer for more detailed description https://github.com/lajanki/quote_randomizer
  * keys.json is an empty storage space for Twitters access tokens, and
  * bot.sh is a Linux launcher script for running bot.py and for sending any generated output to a web server.




#### Changelog
16.6.2016
 * Added frontend folder with PHP scripts responsible for displaying the results
27.2.2016
 * Letter files are now html-encoded for prettier outputting in a website. No need to keep track of line breaks anymore.
 * Signatures are now randomly generated using http://www.behindthename.com/random/
 * File I/O down to 1 file. User input is now entered directly to template rather than stored in a buffer.
15.2.2016
 * Initial release



___
Written on Python 2.7.8

