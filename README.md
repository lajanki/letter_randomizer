# letter_randomizer
Creates randomized letters by filling templates with user input.

## Description

A Python script that generates various types of letters by randomly selecting words to mark as blanks and
then fill the blanks with words of the same class as the original word. Words are categorized into classes such as verbs, nouns and adjectives using the nltk module.

The script is divided into two modules by functionality:
 * letters.py is in charge of reading templates and generating randomized letters, while
 * twitterbot.py handles Twitter interaction and sends the generated file to a dedicated web page at http://lajanki.mbnet.fi/letters/


## Requirements

Python modules:
 * Natural Language Toolkit (nltk):
     http://www.nltk.org/index.html
 * Twython:
     https://twython.readthedocs.org/en/latest/
 * beautifulsoup:
     https://www.crummy.com/software/BeautifulSoup/bs4/doc/

Keys:
* The Twitterbot needs Twitter access tokens and developer keys in bot-data/keys.json, see
 https://dev.twitter.com/oauth/overview/application-owner-access-tokens


## Usage

The letters module can be run directly to generate a randomized letter whose missing words are read from the included database dictionary.db.
```
python letters.py --generate
``` 
chooses a random template from templates/ parses it into a change_frame.json file in the data/ folder which includes some metadata about the words to change, and finally fetches matching words from the database and produces and output in the data/ directory. The output is an html-tagged .txt file.

It is also possible to manually insert input to be parsed for words filling the blanks. First, parse a random template with
```
python letters.py --init
``` 
Then, enter input with
```
--parse-input input
``` 
and the script will insert valid words into a metadata file in data/change_frame.json. The ```--fill-missing``` flag fills any remaining gaps from the database and produces an output file in the data/ folder.

Complete reference:
``` 
  -h, --help           show this help message and exit
  --init               Initialize a random template letter file for
                       processing. Overwrites previous files in /data.
  --generate           Generate a random letter.
  --fill-missing       Fill all missing words with entries from database.
  --parse-input input  Parse string <input> for words to fill gaps in the
                       current letter.
  --show               Show contents of change_frame.json.
 ``` 
The bot twitterbot.py works by generating a letter each time its run, uploads it to the web page and tweets a link to it. It also keeps a dynamic index of template files to process in bot-data/bot_status.json.





#### Changelog
27.1.2017
* Rewrote letters.py as a class to accommodate the ability to run it without affecting the bot's current state.
* Rewrote the bot generate finished files on each run.
* Database behaviour cleanup: added a tagged dataset from the nltk library to the database and removed unrelated tables. Also removed the dependancy to the custom dbaccess module, which was never meant for this project and didn't serve much of a purpose anyway.

23.7.2016
 * Changed letter formatting to markdown. All html parsing is now done by markdown and beautifulsoup.
 * Added a bunch of templates to templates/.
 * Changed to use json for serializing.

9.7.2016
 * Added support for sending new input through the server and simplified input parsing in bot.py and letters.py.

16.6.2016
 * Added frontend folder with PHP scripts responsible for displaying the results.

27.2.2016
 * Letter files are now html-encoded for prettier outputting in a website. No need to keep track of line breaks anymore.
 * Signatures are now randomly generated using http://www.behindthename.com/random/
 * File I/O down to 1 file. User input is now entered directly to template rather than stored in a buffer.

15.2.2016
 * Initial release



___
Written on Python 2.7.8

