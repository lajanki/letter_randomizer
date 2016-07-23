# -*- coding: utf-8 -*-

################################################################################
# letters.py                                                                   #
# Creates randomized letters by reading a letter template from file,           #
# parsing it for words to change and filling in new words from user input.     #
#                                                                              #
# New words are either fetched from a database or parsed from command line 	   #
# arguments. 															       #
#                                                                              #
# The letter template is tokenized and word tagged by the nltk module to       #
# determine which words should be changed as well as making sure that the      #
# right type of word is used to replace old ones (verbs for verbs etc.).       #
# http://www.nltk.org/                                                         #
#                                                                              #
# This script is mostly intended as a library module for bot.py, which uses    #
# Twitter as a user input source, but can be run directly to generate a        #
# randomized letter.                                                           #
#                                                                              #
# File structure:                                                              #
# * This script uses a json encoded file for internal bookkeeping.             #
#	Template data regarding the position and types of words needed is stored   #
#	in template.json                                                           #
# * Additionally the script uses:                                              #
#   1 quotes.db                                                                #
#     a database with a table of words grouped by their class.                 #
#   2 templates                                                                #
#     folder containing letter templates as .txt files                         #
#   3 template/summary.json                                                    #
#     file matching each letter file name to a title/description               #
#																			   #
# Change log 																   #
# 23.7.2016  																   #
#	-Changed letter encoding to markdown for slightly way to add new templates #
#    and a lot simpler processing in parse_letter() and compose_letter(). 	   #
#	 The general procedure to processing a template is now: 				   #
#	   1. Tokenize with nltk,												   #
#	   2. Transform to html with markdown, 									   #
#	   3. Parse the html with BeautifulSoup to add receiver and signatures     #
#   -template.json: instead of storing the whole template, only the actual     #
#	 change data is stored 													   #
# 9.7.2016 																	   #
#	-Parse_input() is now the only access point to inserting new data to       #
#	 template.pkl throughout letters.py and bot.py. 						   #
# 27.5.2016  																   #
#	-Letter files are now html-encoded for prettier outputting in a website.   #
#	 No need to keep track of line breaks anymore.                             #
#	-Signatures are now randomly generated using                               #
#	   http://www.behindthename.com/random/ 	  						       #
#	-File I/O down to 1 file. User input is now entered directly to template   #
#	 rather than stored in a buffer. 										   #
# 13.2.2016  																   #
# 	-Initial release. 														   #
#                                                                              #
################################################################################

import requests
import bs4
import markdown
import nltk
import json
import argparse
import os
import glob
import time
import pprint
import codecs
import random
import sqlite3 as lite


# define valid nltk word classes for switches
CLASSES = ["JJ", "JJR", "JJS", "NN", "NNS", "RB", "RBR", "VB", "VBN", "VBD", "VBG"]
rpi_path = "/home/pi/python/letters/"


def parse_letter(template, splice_percentage = 0.35):
	"""Read a markdown encoded letter template from file, randomly select the words to change from each paragraph
	and store tokenized template and change data to file
	Args:
		template (string): path to template file
		splice_percentage (float): percentage of valid queries to pass to autocomplete
	"""
	# decode template to unicode
	with codecs.open(template, encoding="utf8") as f:
		text = f.read()

	# nltk.word_tokenze() ignores newline characters. To keep record of paragraphs,
	# split text by newlines
	text = text.split("\n")

	# define characters for words that should be ignored when determining valid nltk tags
	# most of these shouldn't have a valid tag anyway
	html_items = [ 
		"<",
		">",
		"span",
		"class",
		"id",
		"signature",
		"receiver",
		"/",
		"#",
		"@"
	]
	# tokenize each paragraph to create a frame of words to change
	change_frame = []
	for pidx, p in enumerate(text):
		tokens = nltk.word_tokenize(p)
		tagged = nltk.pos_tag(tokens)

		# a list of (paragraph_idx, word_idx, nltk_tag) tuples from words valid words
		valid = [(pidx, idx, token[1]) for idx, token in enumerate(tagged) if token[1] in CLASSES
			and not any(item in token[0] for item in html_items) ]

		# randomly select splice_precentage% of valid tags
		n = int(splice_percentage * len(valid))
		# create a tuple of (paragraph index, [word index, nltk tag]) to add to change_frame
		p_token = random.sample(valid, n)
		if p_token:
			change_frame.extend(p_token)

	# read title from templates/summary.json
	with open(rpi_path+"templates/summary.json", "r") as summary_file:
		summary = json.load(summary_file)
		fname = os.path.basename(template)
	try:
		title = summary[fname]
	except KeyError as e:  # title not inserted in summary.json
		print e
		title = ""  

	d = {"title":title, "file":template, "change_frame":change_frame, "input":[]}
	with open(rpi_path+"template.json", "wb") as template_file:
		json.dump(d, template_file)

	return title


def parse_input(s, first_only=True):
	"""Parse input for words needed to fill missing data in template.pkl.
	Modifies template.json
	Arg:
		s (string): text to use as input
		first_only (boolean): whether only the first valid word of a tweet should be parsed
	"""
	with open(rpi_path+"template.json", "rb") as template_file:
		template_data = json.load(template_file)
		change_frame = template_data["change_frame"]
		input_ = template_data["input"]

	# don't procede to call nltk if all gaps already filled
	if not change_frame:
		return


	print "Parsing:", s
	tokens = nltk.word_tokenize(s)
	# drop tokens with unwanted characters
	tokens = [ token for token in tokens if not any(item in token for item in ["//", "html", "@", "http"]) ]
	# should only the first word be considered?
	if first_only:
		tokens = tokens[:1]
	tagged = nltk.pos_tag(tokens)

	# check if tagged words match those needed to fill blanks
	for word, tag in tagged:
		# get all change_frame tuples with matching tag
		valid = [token for token in change_frame if token[2] == tag]

		# replace the topmost item in valid with the tagged word
		if valid:
			data = valid.pop()
			new = (data[0], data[1], word) # (paragraph_idx, word_idx, word)
			#print new
		
			# add new word to input and remove old data from change_frame
			input_.append(new)
			change_frame.remove(data)

	# store new change_frame and template back to file
	#d = {"template":template, "change_frame":change_frame}
	template_data["change_frame"] = change_frame
	template_data["input"] = input_
	with open(rpi_path+"template.json", "wb") as template_file:
		json.dump(template_data, template_file)


def fill_missing():
	"""Read missing word data from template.json and fetch matching words from database.
	Fill new data in template and set change_frame to None.
	Note: does not generate an actual letter file, see compose_letter().
	Modifies template.json
	"""
	with open(rpi_path+"template.json", "rb") as template_file:
		template_data = json.load(template_file)
		change_frame = template_data["change_frame"]
		input_ = template_data["input"]

	con = lite.connect(rpi_path+"quotes.db")
	cur = con.cursor()
	with con: 
		# loop over change_frame and fetch a matching word from database to fill each slot
		for pidx, idx, tag in change_frame:
			cur.execute("SELECT word, class FROM dictionary WHERE class = ? ORDER BY RANDOM() LIMIT 1", (tag,))
			row = cur.fetchone()
			new = row[0]

			# add new word to input_
			#print("replace:")
			input_.append( (pidx, idx, new) )

	# empty change_frame and store new data back to file
	template_data["change_frame"] = None
	template_data["input"] = input_
	with open(rpi_path+"template.json", "wb") as template_file:
		json.dump(template_data, template_file)


def compose_letter():
	"""Join template data to create a html-tagged letter.
	Return:
		the letter as a string.
	"""
	with open(rpi_path+"template.json", "rb") as template_file:
		template_data = json.load(template_file)
		input_ = template_data["input"]
		title = template_data["title"]
		template = template_data["file"]

	# open the current template, tokenize each paragraph and
	# insert new words
	with open(template) as f:
		text = f.read()
	text = text.split("\n")

	# create a new letter by filling each paragraph,
	# use nltk.word_tokenize() to get the correct indices of words to insert
	letter = []
	for pidx, p in enumerate(text):
		# before tokenizing, check if the paragraph end with two spaces to mark a line break for markdown,
		# nltk.word_tokenize() will lose these
		linebreak = False
		if p.endswith("  "):
			linebreak = True
		tokenized = nltk.word_tokenize(p)
		# get new words belonging to this paragraph
		new = [ item for item in input_ if item[0] == pidx ]
		for token in new:
			tokenized[token[1]] = token[2]

		# add back the spaces
		joined = " ".join(tokenized)
		if linebreak:
			joined += "  "

		letter.append(joined)

	# join the paragraps together with newlines
	letter = "\n".join(letter)

	# define replacements for trimming whitespaces around punctuation and html tags
	# use a list to keep the order intact when iterating
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
			("< span class= '' receiver '' >", "<span class=\"receiver\">"),
			("< span class= '' receiver first '' >", "<span class=\"receiver first\">"),
			("< span class= '' signature '' >", "<span class=\"signature\">"),
			("< span class= '' signature first '' >", "<span class=\"signature first\">"),
			(" < /span >", "</span>"),
			(" '", "'")
		]
	for token in replacements:
		letter = letter.replace(token[0], token[1])

	# process to html via markdown and remove extra newline characters between paragraphs
	letter = markdown.markdown(letter)
	letter = letter.replace("\n", "")

	# Finally using beautifulsoup check if a receiver name or a signature should be added:
	soup = bs4.BeautifulSoup(letter, "lxml")
	# use a css selector to get the receiver,
	# by default generate only the last name
	receiver = soup.select("span.receiver")
	for tag in receiver:
		if "first" in tag["class"]:
			tag.string = generate_name(first_only=True)
		else:
			tag.string = generate_name(last_only=False)

	# signatures,
	# usually full name
	signature = soup.select("span.signature")
	for tag in signature:
		if "first" in tag["class"]:
			tag.string = generate_name(first_only=True)
		else:
			tag.string = generate_name()


	# get the contents of soup.body as a string
	contents = soup.body.contents
	letter = "".join([unicode(p) for p in contents])  # elements of contents are BeautifulSoup Tags, cast to unicode


	# use timestamp to generate a filename for output
	timestamp = time.strftime("%d.%m.%y")
	timestamp = timestamp.replace(".", "_")
	title = title.replace(" ", "_")
	fname = title + "_" + timestamp + ".txt"
	with open(fname, "wb") as output:
		output.write(letter.encode("utf8"))


def randomize_letter():
	"""Select a random template from templates, parse and randomize it with fill_missing()."""
	files = glob.glob(rpi_path+"templates/*.txt")
	letter = random.choice(files)
	print "Using", letter
	parse_letter(letter)
	fill_missing()
	compose_letter()


#==================================================================================
# Helper functions =
#===================
def show_files():
	"""Show contents of template.pkl and input.pkl."""
	with open(rpi_path+"template.json", "rb") as template_file:
		template_data = json.load(template_file)  

	print "input:"
	pprint.pprint(template_data["input"])

	print "change_frame:"
	pprint.pprint(template_data["change_frame"])

	return template_data


def get_template_status():
	"""Check how many words are still needed to fill the current template.
	Return:
		a string describing how many adjectives, nouns, verbs and adverbs are needed
	"""
	with open(rpi_path+"template.json", "rb") as template_file:
		template_data = json.load(template_file)
		change_frame = template_data["change_frame"]

	# no more words needed, return an empty string
	if not change_frame:
		return ""

	# create a dict to map tags to number of matching words needed
	tags = [token[2] for token in change_frame]
	d = dict.fromkeys(CLASSES, 0)
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


def html_format(string, tag):
	"""Enclose string in tags.
	Return
		a html-tagged string
	"""
	return u"<{0}>{1}</{0}>".format(tag, string)


def generate_name(nfirst_names = 1, first_only=False, last_only=False):
	"""Use requests on http://www.behindthename.com/random/ to generate a name.
	Args:
		nfirst_names (int): number first names the result should have
		first_only (boolean): whether only the first name should be returned
		last_only (boolean): whether only the last name should be returned
	Return:
		the generated name
	"""

	# set name parameters,
	# first + middle + surname
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

	# get the text value of each <a> element having class "plain"
	names = [a.text for a in soup.find_all("a", class_="plain")]
	if first_only:
		return names[0]
	if last_only:
		return names[-1]
	return " ".join(names)


def parse_for_dictionary(fname):
	"""Parse given template file for database dictionary.
	Arg:
		fname (string): filename, or part of a name, to parse or * for all templates
	"""
	import dbaccess

	files = glob.glob(rpi_path+"templates/*.txt")
	if fname == "all":
		files_to_parse = files
	else:
		files_to_parse = [ file for file in files if fname in file ]

	# parse html with beatifulSoup
	for file in files_to_parse:
		print "parsing", file
		soup = bs4.BeautifulSoup(open(file), "lxml")
		s = soup.text.replace("\n", " ")

		dbaccess.parse_for_dictionary(s)
	dbaccess.database_size()


#==================================================================================
# Main =
#=======
if __name__ == "__main__":
	parser = argparse.ArgumentParser(description="Letter randomizer.")
	parser.add_argument("--init", help="Drop all current working data and process the next template.", action="store_true")
	parser.add_argument("--random-letter", help="Generate a random letter", action="store_true")
	parser.add_argument("--fill-missing", help="Fill all missing template entries from database", action="store_true")
	parser.add_argument("--parse-input", help="Parse string <input> for words to fill gaps in processed template.", metavar="input")
	parser.add_argument("--parse-templates", help="""Parse the contents of <template> for database dictionary.
			<template> should be filename, a string matching to a filename or 'all' for all templates to be parsed.""", metavar="template")
	parser.add_argument("--show", help="Show contents of input.pkl.", action="store_true")
	args = parser.parse_args()

	if args.init or not os.path.isfile(rpi_path+"template.pkl"):
		print "Initializing..."
		files = glob.glob(rpi_path+"templates/*.txt")
		letter = random.choice(files)
		print "Using", letter
		parse_letter(letter)

	elif args.parse_input:
		#parse_input("Here are your sealions, sir.")
		parse_input(args.parse_input)

	elif args.parse_templates:
		parse_for_dictionary(args.parse_templates)

	elif args.fill_missing:
		fill_missing()

	elif args.show:
		show_files()

	elif args.random_letter:
		randomize_letter()

	else:
		parser.print_help()




	



