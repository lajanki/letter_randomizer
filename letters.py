# -*- coding: utf-8 -*-

"""
letters.py
Creates randomized letters by reading a letter template from file,
parsing it for words to change and filling in new words from user input
or from a database.

The letter template is tokenized and word tagged by the nltk module to
determine which words should be changed as well as making sure that the
right type of word is used to replace the chosen ones (ie. verbs for verbs etc.).
http://www.nltk.org/

User input can be directly entered as a command line argument, but is mostly
meant to be gathered from other sources (originally I wrote this to ask input
from Twitter). Running this module directly is mainly meant to generate a
complete letter using the provided database dictionary.db as a source. The database consists
mostly of tagged data from the nltk library. (Originally it served as a data source
for another project).

File structure:
* The templates folder contains various example letter files collected from
  various internet sources.
* Parsing a templete creates an internal bookkeeping file in the data folder:
	change_frame.json contains information about the position and type of words
	that needs to changed.
* The generated letters are also stored in the data folder
* dictionary.db is a database that can be used as an input source

Requirements:
* nltk - http://www.nltk.org/install.html
* markdown - http://pythonhosted.org/Markdown/install.html
* beautifulsoup - https://www.crummy.com/software/BeautifulSoup/bs4/doc/


Change log
27.1.2017
* Rewritten as a class in order to provide a way to keep the bot's data files
  separate from running this module on its own.
* Cleaned up some comments (copy pasting functions from other files and not changing
  their description can be somewhat confusing)
23.7.2016 
* Changed letter encoding to markdown for slightly way to add new templates
  and a lot simpler processing in parse_letter() and compose_letter().
  The general procedure to processing a template is now:
	1. Tokenize with nltk,
	2. Transform to html with markdown,
	3. Parse the html with BeautifulSoup to add receiver and signatures
* Changed serializing method in template.json to json for readability
* Instead of storing the whole template, store only the words
  needed to fill the current template

9.7.2016
* parse_input() is now the only access point to inserting new data to
  template.pkl throughout letters.py and bot.py.
27.5.2016
* Letter files are now html-encoded for prettier outputting in a website.
  No need to keep track of line breaks anymore.
* Signatures are now randomly generated using
  http://www.behindthename.com/random/
* File I/O down to 1 file. User input is now entered directly to template
  rather than stored in a buffer.
13.2.2016
* Initial release.
"""


import requests
import json
import argparse
import glob
import time
import pprint
import codecs
import random
import os.path

import nltk
import markdown
import bs4

import sqlite3 as lite


class LetterRandomizer():


	# Define valid nltk word tags for switching.
	TAGS = ("JJ", "JJR", "JJS", "NN", "NNS", "RB", "RBR", "VB", "VBN", "VBD", "VBG")

	def __init__(self, path, wd = "data/"):
		"""Defines file paths to auxilary files."""
		self.base = path # path to the toplevel directory where all folders lie
		self.wd = path + wd  # working directory: generated letters + change_frame data gets stored here. (the bot gets its own folder)
		self.frame = self.wd + "change_frame.json"


	def parse_letter(self, template, splice_percentage = 0.35):
		"""Processes a letter template to a change frame. Reads a markdown encoded letter from file,
		randomly selects the indices of words to change from each paragraph and stores the result
		to a change_frame.json file.
		Args:
			template (string): path to the template file
			splice_percentage (float): percentage of words to change
		Return:
			the title for the finished letter
		"""
		# Decode template as a unicode object.
		with codecs.open(template, encoding="utf8") as f:
			text = f.read()

		# nltk.word_tokenze() ignores newline characters. To keep track of paragraphs,
		# split text by newlines.
		text = text.split("\n")

		# Define characters for words that should be ignored when determining nltk tags,
		# most of these shouldn't receive a valid tag anyway.
		invalid_tokens = [ 
			"<",
			">",
			"span",
			"class",
			"id",
			"signature",
			"receiver",
			"/",
			"#",
			"@",
			"`",
			"'"
		]
		# Tokenize each paragraph to create a frame of words to change.
		change_frame = []
		for pidx, p in enumerate(text):
			# Replace occurances of ' to ` in order to keep nltk from tokenizing contractions
			# into two (ie. "they're" -> ["they", "'re"]). The former part could then be chosen
			# to be a valid switch word.
			#p = p.replace("'", "`")  # update: normalize_tokens takes care of this
			tokens = LetterRandomizer.normalize_tokens(nltk.word_tokenize(p))
			tagged = nltk.pos_tag(tokens)

			# A list of (paragraph_idx, word_idx, nltk_tag) tuples from words valid words.
			valid = [(pidx, idx, token[1]) for idx, token in enumerate(tagged) if token[1] in LetterRandomizer.TAGS
				and not any(item in token[0] for item in invalid_tokens) ]

			# Randomly select splice_precentage% of valid tags.
			n = int(splice_percentage * len(valid))
			# Create a tuple of (paragraph index, [word index, nltk tag]) to add to change_frame.
			p_token = random.sample(valid, n)
			if p_token:
				change_frame.extend(p_token)

		# Read this template's title from templates/summary.json.
		with open(self.base + "templates/summary.json", "r") as f:
			summary = json.load(f)
			fname = os.path.basename(template)
		try:
			title = summary[fname]

		# Title not found in summary.json:
		# use the filename as title.
		except KeyError as e:
			print e
			title = fname 

		# Store parsed data to change_frame.json.
		d = {"title":title, "file":template, "change_frame":change_frame, "input":[]}
		with open(self.frame, "w") as f:
			json.dump(d, f)

		return title


	def parse_input(self, s, first_only=False):
		"""Parses input s for words needed to fill missing data in change_frame.json.
		Arg:
			s (string): text to use as input
			first_only (boolean): only parse the first word?
		"""
		with open(self.frame) as f:
			template_data = json.load(f)
			change_frame = template_data["change_frame"]
			input_ = template_data["input"]

		# Don't procede to call nltk if all gaps already filled.
		if not change_frame:
			return

		print "Parsing:", s
		tokens = LetterRandomizer.normalize_tokens(nltk.word_tokenize(s))
		# Drop tokens with unwanted characters.
		tokens = [ token for token in tokens if not any(item in token for item in ("//", "html", "@", "http")) ]
		# Should only the first word be considered?
		if first_only:
			tokens = tokens[:1]
		tagged = nltk.pos_tag(tokens)

		# Check if tagged words match those needed to fill blanks.
		for word, tag in tagged:
			# Get all change_frame tuples with matching tag.
			valid = [token for token in change_frame if token[2] == tag]

			# Replace the topmost item in valid with the tagged word.
			if valid:
				data = valid.pop()
				new = (data[0], data[1], word) # (paragraph_idx, word_idx, word)
				#print new
			
				# Add new word to input and remove old data from change_frame.
				input_.append(new)
				change_frame.remove(data)

		# Store new change_frame and template back to file.
		#d = {"template":template, "change_frame":change_frame}
		template_data["change_frame"] = change_frame
		template_data["input"] = input_
		with open(self.frame, "w") as f:
			json.dump(template_data, f)


	def fill_missing(self):
		"""Reads missing word data from change_frame.json and fetches matching words from the database.
		Note: does not generate an actual letter file, see compose_letter().
		"""
		with open(self.frame, "r") as f:
			template_data = json.load(f)
			change_frame = template_data["change_frame"]
			input_ = template_data["input"]

		if not change_frame:
			return

		con = lite.connect(self.base + "dictionary.db")
		cur = con.cursor()
		with con: 
			# Loop over change_frame and fetch a matching word from database to fill each slot.
			for pidx, idx, tag in change_frame:
				cur.execute("SELECT word, class FROM dictionary WHERE class = ? ORDER BY RANDOM() LIMIT 1", (tag,))
				row = cur.fetchone()
				new = row[0]

				# Add new word to input_.
				#print("replace:")
				input_.append( (pidx, idx, new) )

		# Empty change_frame and store new data back to file.
		template_data["change_frame"] = None
		template_data["input"] = input_
		with open(self.frame, "w") as f:
			json.dump(template_data, f)


	def compose_letter(self):
		"""Joins template data from change_frame.json to create an html-tagged letter.
		Created letter is saved as a .txt file.
		Return:
			the filepath to the generated file
		"""
		with open(self.frame, "r") as f:
			template_data = json.load(f)
			input_ = template_data["input"]
			title = template_data["title"]
			template = template_data["file"]

		# Open current change_frame, tokenize each paragraph and
		# insert new words.
		with codecs.open(template, encoding="utf8") as f:
			text = f.read()
		text = text.split("\n")

		# Create a new letter by filling each paragraph,
		# use nltk.word_tokenize() to get the correct indices of words to insert.
		letter = []
		for pidx, p in enumerate(text):
			# Before tokenizing, check if the paragraph ends with two spaces to mark a line break for markdown,
			# nltk.word_tokenize() will lose these.
			linebreak = False
			if p.endswith("  "):
				linebreak = True
			tokenized = LetterRandomizer.normalize_tokens(nltk.word_tokenize(p))
			# Get new words belonging to this paragraph,
			# guard against index error for mismatched paragraph indices.
			try:
				new = [ item for item in input_ if item[0] == pidx ]
				for token in new:
					tokenized[token[1]] = token[2]

				# Add back the two spaces at the end of the paragraph.
				joined = " ".join(tokenized)
				if linebreak:
					joined += "  "

				letter.append(joined)
			except IndexError as e:
				print e
				print "current file: ", template

		# Join the paragraps together with newlines.
		letter = "\n".join(letter)

		# Define replacements for trimming whitespaces around punctuation and html tags.
		# Use a list to keep the order intact when iterating.
		replacements = [
				(" ,", ","),
				(" .", "."),
				(" !", "!"),
				(" ?", "?"),
				(" :", ":"),
				(" ;", ";"),
				(" )", ")"),
				("( ", "("),
				("$ ", "$"),
				(" @ ", "@"),
				("# #", "##"),
				("< span class='' receiver'' >", "<span class=\"receiver\">"), # normalize_tokens() will left shift the 's
				("< span class='' receiver first'' >", "<span class=\"receiver first\">"),
				("< span class='' signature'' >", "<span class=\"signature\">"),
				("< span class='' signature first'' >", "<span class=\"signature first\">"),
				(" < /span >", "</span>"),
				(" '", "'")
			]
		for token in replacements:
			letter = letter.replace(token[0], token[1])

		# Process to html via markdown and remove extra newline characters between paragraphs.
		letter = markdown.markdown(letter)
		letter = letter.replace("\n", "")

		# Finally, using beautifulsoup, check if a receiver name or a signature should be added:
		soup = bs4.BeautifulSoup(letter, "lxml")
		receiver = soup.select("span.receiver")
		# Receiver.
		for tag in receiver:
			if "first" in tag["class"]:
				tag.string = LetterRandomizer.generate_name(first_only=True)
			else:
				tag.string = LetterRandomizer.generate_name(last_only=False)

		# Signatures, usually full name.
		signature = soup.select("span.signature")
		for tag in signature:
			if "first" in tag["class"]:
				tag.string = LetterRandomizer.generate_name(first_only=True)
			else:
				tag.string = LetterRandomizer.generate_name()


		# Get the contents of soup.body as a string.
		contents = soup.body.contents
		letter = "".join([unicode(p) for p in contents])  # elements of contents are BeautifulSoup Tags, cast to unicode


		# Generate a filename with a timestamp
		timestamp = time.strftime("%d.%m.%y")
		timestamp = timestamp.replace(".", "_")
		title = title.replace(" ", "_")
		fname = title + "_" + timestamp + ".txt"
		path = self.wd + fname
		with codecs.open(path, "w", encoding="utf8") as f:
			f.write(letter)

		return path


	def randomize_letter(self):
		"""Generate a randomized letter by selecting a random template and
		processing with fill_missing.
		Return:
			a tuple of the title of the letter and its filepath
		"""
		files = glob.glob(self.base + "templates/*.txt")
		letter = random.choice(files)
		print "Generating a letter from", letter
		title = self.parse_letter(letter)
		self.fill_missing()
		path = self.compose_letter()

		return title, path


	#==================================================================================
	# Helper functions =
	#===================

	def show_files(self):
		"""Show contents of template.json."""
		with open(self.frame, "r") as f:
			template_data = json.load(f)  

		print "input:"
		pprint.pprint(template_data["input"])

		print "change_frame:"
		pprint.pprint(template_data["change_frame"])


	def get_template_status(self):
		"""Checks how many words are still needed to fill change_frame.
		Return:
			a string describing how many adjectives, nouns, verbs and adverbs are needed
		"""
		with open(self.frame, "r") as f:
			template_data = json.load(f)
			change_frame = template_data["change_frame"]

		# no more words needed, return an empty string
		if not change_frame:
			return ""

		# create a dict to map tags to number of matching words needed
		tags = [token[2] for token in change_frame]
		d = dict.fromkeys(LetterRandomizer.TAGS, 0)
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


	@staticmethod
	def html_format(string, tag):
		"""Enclose string in tags.
		Return
			a html-tagged string
		"""
		return u"<{0}>{1}</{0}>".format(tag, string)


	@staticmethod
	def generate_name(nfirst_names = 1, first_only=False, last_only=False):
		"""Use requests on http://www.behindthename.com/random/ to generate a name.
		Args:
			nfirst_names (int): number first names the result should have
			first_only (boolean): whether only the first name should be returned
			last_only (boolean): whether only the last name should be returned
		Return:
			the generated name
		"""

		# S.et name parameters,
		# first + middle + surname.
		name_params = {
			"number":nfirst_names,
			"gender":"both",
			"randomsurname":"yes",
			"all":"no",
			"usage_chi":1,
			"usage_dan":1,
			"usage_dut":1,
			"usage_end":1,
			"usage_est":1,
			"usage_get":1,
			"usage_hun":1,
			"usage_ind":1,
			"usage_ita":1,
			"usage_jew":1,
			"usage_nor":1,
			"usage_per":1,
			"usage_rus":1,
			"usage_spa":1
		}
		r = requests.get("http://www.behindthename.com/random/random.php", params=name_params)

		soup = bs4.BeautifulSoup(r.text, "lxml")

		# Get the text value of each <a> element having class "plain".
		names = [a.text for a in soup.find_all("a", class_="plain")]
		if first_only:
			return names[0]
		if last_only:
			return names[-1]
		return " ".join(names)


	@staticmethod
	def normalize_tokens(tokens):
		"""nltk.word_tokenize() will tokenize words using ' as an apostrophe into
		two tokens: eg. "can't" -> ["can", "'t"].
		This function normalizes tokens by reattaching the parts back together.
		When parsing input for change_frame this prevents the separate parts from being marked as
		valid tokens.
		Arg:
			tokens (list):  a tokenized list of a quote
		Return:
			a list of the normalized tokens
		"""
		for idx, token in enumerate(tokens):
			try:
				if "'" in token:
					tokens[idx-1] += tokens[idx]
					tokens[idx] = "DEL"
			except IndexError as e:
				print e

		normalized = [token for token in tokens if token != "DEL"]
		return normalized



#==================================================================================
# Main =
#=======
if __name__ == "__main__":
	parser = argparse.ArgumentParser(description="Letter randomizer.")
	parser.add_argument("--init", help="Initialize a random template letter file for processing. Overwrites previous files in /data.", action="store_true")
	parser.add_argument("--generate", help="Generate a random letter.", action="store_true")
	parser.add_argument("--fill-missing", help="Fill all missing words with entries from database.", action="store_true")
	parser.add_argument("--parse-input", help="Parse string <input> for words to fill gaps in the current letter.", metavar="input")
	parser.add_argument("--show", help="Show contents of change_frame.json.", action="store_true")
	args = parser.parse_args()

	randomizer = LetterRandomizer("/home/pi/python/letters/")

	if args.init:
		print "Initializing..."
		files = glob.glob(randomizer.base + "templates/*.txt")
		letter = random.choice(files)
		print "Using", letter
		randomizer.parse_letter(letter)
		print "Template data stored in " + randomizer.wd
		print "Use --parse-input or --fill-missing to enter input for the letter."

	elif args.generate:
		title, path = randomizer.randomize_letter()
		print "Stored at " + path

	elif args.fill_missing:
		try:
			print "Fetching missing words from the database..." 
			randomizer.fill_missing()
			letter = randomizer.compose_letter()
			print "Generated a new letter at " + letter
		except IOError as e:
			print e
			print "Initialize first with --init"

	elif args.parse_input:
		try:
			#parse_input("Here are your sealions, sir.")
			randomizer.parse_input(args.parse_input)
		except IOError:
			print "Initialize first with --init"

	elif args.show:
		try:
			randomizer.show_files()
			print randomizer.get_template_status()
		except IOError:
			print "There's nothing to show. Initialize first with --init"


	else:
		parser.print_help()




		



