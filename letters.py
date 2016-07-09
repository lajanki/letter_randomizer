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
# * This script uses a Pickle encoded file for internal bookkeeping.           #
#	Template data regarding the position and types of words needed is stored   #
#	in template.pkl                                                            #
# * Additionally the script uses:                                              #
#   1 quotes.db                                                                #
#      a database with a table of words grouped by their class.                #
#   2 templates                                                                #
#     folder containing letter templates as .txt files                         #
#   3 template/summary.json                                                    #
#     file matching each letter file name to a title/description               #
#																			   #
# Change log 																   #
# 9.7.2016 																	   #
#	-parse_input() is now the only access point to inserting new data to       #
#	 template.pkl throughout letters.py and bot.py. 						   #
# 27.5.2016  																   #
#	-Letter files are now html-encoded for prettier outputting in a website.   #
#	  No need to keep track of line breaks anymore.                            #
#	-Signatures are now randomly generated using                               #
#	   http://www.behindthename.com/random/ 	  						       #
#	-File I/O down to 1 file. User input is now entered directly to template   #
#	  rather than stored in a buffer. 										   #
# 13.2.2016  																   #
# 	-Initial release. 														   #
#                                                                              #
################################################################################

import requests
import pprint
import bs4
import nltk
import random
import pickle
import json
import argparse
import sys
import os
import glob
import time
import sqlite3 as lite


# define valid nltk word classes for switches
CLASSES = ["JJ", "JJR", "JJS", "NN", "NNS", "RB", "RBR", "VB", "VBN", "VBD", "VBG"]
rpi_path = "/home/pi/python/letters/"


def parse_letter(letter, splice_percentage = 0.35):
	"""Read a letter template from file, randomly select the words to change from each paragraph
	and store tokenized template and change data to file
	Args:
		letter (string): path to letter template
		splice_percentage (float): the percentage of valid words from each paragraph to use for changing
	Return:
		The title of the letter as read from templates/summary.json
	"""
	soup = bs4.BeautifulSoup(open(letter), "lxml")
	# store tags and their data to list
	html_tagged = soup.find_all(["h2", "p", "li"])
	
	# nltk tag each paragraph (==html tagged section)
	tokens = [(nltk.word_tokenize(token.text), token.name, token.parent.name) for token in html_tagged]
	#pprint.pprint(tokens[2])  # ([words], html_tag)

	tagged = [(nltk.pos_tag(token[0]), token[1]) for token in tokens]
	#pprint.pprint(tagged[2])  # ([(word, tag)], html_tag)


	change_frame = [] # frame for words to change in each paragraph
	# loop over each paragraph to determine words to change
	# (paragraph index, (tagged paragraph, html_tag))
	for pidx, (tagged_list, html_tag) in enumerate(tagged):
		valid = []
		for idx, item in enumerate(tagged_list):
			if item[1] in CLASSES:
				valid.append((pidx, idx, item[1]))   # (paragraph index, word index, tag) 

		k = int(splice_percentage * len(valid))
		change = random.sample(valid, k)

		# add change data to frame
		change_frame.extend(change)

	# check if template contains a signature, generate a new one and replace the old one
	signature = soup.select("span.signature")
	#print signature
	for name in signature:
		# find the p tagged paragraph containing the signature. Generate a new signature
		# and add the <span> tags eround it
		name = name.text 
		name = name.split()  # split name to a list
		try:
			new_name = generate_name()
		except requests.exceptions.ConnectionError as e:
			print e, "Using old name"
			new_name = name

		# find the paragraph in tokens with the signature
		idx = [i for i, paragraph in enumerate(tokens) if set(name) < set(paragraph[0])][0]  # list of 1
		# find the index of the first name within tokens[idx][0]
		name_idx = tokens[idx][0].index(name[0])
		# write new data to tokens
		tokens[idx][0][name_idx] = "<br/><span class=\"signature\">"+new_name+"</span>"
		tokens[idx][0][name_idx+1] = "<br/>"

	# find paragraph indices of first and last <li> items in a list
	list_start = []  # (paragraph_idx, parent_tag)
	list_end = []
	for list_ in soup.select("ul, ol"):
		# list_ contains newline characters as items, exclude them
		items = [i for i in list_.contents if i != "\n"]

		# find the first and last list item in tokens and
		# store the info in a list
		first = items[0].text
		last = items[-1].text
		tag = items[0].parent.name

		idx = tokens.index((nltk.word_tokenize(first), "li", tag))
		list_start.append((idx, tag))
		idx = tokens.index((nltk.word_tokenize(last), "li", tag))
		list_end.append((idx, tag))

	# read title from templates/summary.json
	with open(rpi_path+"templates/summary.json", "r") as summary_file:
		summary = json.load(summary_file)
		fname = os.path.basename(letter)
	try:
		title = summary[fname]
	except KeyError as e:  # title not inserted in summary.json
		print e
		title = ""  


	# store tokens of original template and change_frame to file
	# tokens: [ ([words], html_tag) ]
	# change_frame: [ [(idx, nltk_tag)] ] 
	d = {"template":tokens, "title":title, "change_frame":change_frame, "list_metadata": {"start":list_start, "end":list_end}}
	with open(rpi_path+"template.pkl", "wb") as template_file:
		pickle.dump(d, template_file, 2)

	return title


def parse_input(s, first_only=True):
	"""Parse input for words needed to fill missing data in template.pkl.
	Modifies template.pkl
	Arg:
		s (string): text to use as input
		first_only (boolean): whether only the first valid word of a tweet should be parsed
	"""
	with open(rpi_path+"template.pkl", "rb") as template_file:
		template_data = pickle.load(template_file)
		change_frame = template_data["change_frame"]
		template = template_data["template"]

	# don't procede to call nltk if all gaps already filled
	if not change_frame:
		return

	if s:
		print "Parsing", s
	tokens = nltk.word_tokenize(s)
	# drop tokens with unwanted characters
	tokens = [ token for token in tokens if not any(item in token for item in ["//", "html", "@", "http"]) ]
	# should only the first word be considered?
	if first_only:
		tokens = tokens[:1]
	tagged = nltk.pos_tag(tokens)

	# check if tagged words match those needed to fill blanks
	for word, tag in tagged:
		# get change_frame tuples with matching tag
		valid = [token for token in change_frame if token[2] == tag]

		# replace the topmost item in valid with the tagged word
		if valid:
			data = valid.pop()
			new = (word, (data[0], data[1])) # (word, (paragraph index, word index))
			old = template[data[0]][0][data[1]]

			# add new word to template and remove old data from change_frame
			print "Adding:", new[0], "as", old
			template[data[0]][0][data[1]] = new[0]
			change_frame.remove(data)

	# store new change_frame and template back to file
	#d = {"template":template, "change_frame":change_frame}
	template_data["template"] = template
	template_data["change_frame"] = change_frame
	with open(rpi_path+"template.pkl", "wb") as template_file:
		pickle.dump(template_data, template_file, 2)


def fill_missing():
	"""Read missing word data from template.pkl and fetch matching words from database.
	Fill new data in template and set change_frame to None. Note, does not generate an
	actual letter file - see compose_letter().
	"""
	with open(rpi_path+"template.pkl", "rb") as template_file:
		template_data = pickle.load(template_file)
		change_frame = template_data["change_frame"]
		template = template_data["template"]

  	con = lite.connect(rpi_path+"quotes.db")
	cur = con.cursor()
	with con: 
		# loop over change_frame and fetch a matching word from database to fill each slot
		for pidx, idx, tag in change_frame:	 # (paragraph index, word index, tag)
			cur.execute("SELECT word, class FROM dictionary WHERE class = ? ORDER BY RANDOM() LIMIT 1", (tag,))
			row = cur.fetchone()
			new = row[0]

			# assign new word in template
			#print("replace:")
			#print(template[pidx][0][idx], "->", new)
			template[pidx][0][idx] = new

	# empty change_frame and store new data back to file
	template_data["change_frame"] = None
	template_data["template"] = template
	with open(rpi_path+"template.pkl", "wb") as template_file:
		pickle.dump(template_data, template_file, 2)


def compose_letter():
	"""Join template data to create a html-tagged letter.
	Return:
		the letter as a string.
	"""

	with open(rpi_path+"template.pkl", "rb") as template_file:
		template_data = pickle.load(template_file)
		template = template_data["template"]
		list_metadata = template_data["list_metadata"]
		title = template_data["title"]

	# define replacements for trimming whitespaces around punctuation
	replacements = {" ,":",", " .":".", " !":"!", " ?":"?", " :": ":", " ;":";", " )":")", "( ":"(", "$ ":"$", "* ":"*", " @ ":"@", " '":"'"}
	li_start = list_metadata["start"]
	li_end = list_metadata["end"]

	start_idx = [i for (i, tag) in li_start]
	end_idx = [i for (i, tag) in li_end]

	s = html_format(title, "h1") # add title to beginning
	letter = []
	for idx, paragraph in enumerate(template):
		# join list of words to string
		text = " ".join(paragraph[0])
		# trim whitespace
		for old, new in replacements.iteritems():
			text = text.replace(old, new)
		# wrap in html
		text = html_format(text, paragraph[1])

		# see current paragraph is the first/last <li> element and add the correct <ul>, <ol> tag
		if idx in start_idx:
			i = start_idx.index(idx)
			tag = li_start[i][1]
			text = "<{}>{}".format(tag, text)
		elif idx in end_idx:
			i = end_idx.index(idx)
			tag = li_end[i][1]
			text = "{}</{}>".format(text, tag)

		letter.append(text)

		s += text

	# use timestamp to generate a filename for output
	timestamp = time.strftime("%d.%m.%y")
	timestamp = timestamp.replace(".", "_")
	title = title.replace(" ", "_")
	fname = title + "_" + timestamp + ".txt"
	with open(rpi_path+fname, "wb") as output:
		output.write(s.encode("utf8"))

	return s


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
	with open(rpi_path+"template.pkl", "rb") as template_file:
 		template_data = pickle.load(template_file)  

	print "template:"
	pprint.pprint(template_data["template"])

	print "change_frame:"
	pprint.pprint(template_data["change_frame"])


def html_format(string, tag):
	"""Enclose string in tags.
	Return
		a html-tagged string
	"""
	return u"<{0}>{1}</{0}>".format(tag, string)


def generate_name(nfirst_names = 1, first_only=False):
	"""Use requests on http://www.behindthename.com/random/ to generate a name.
	Arg:
		nfirst_names (int): number first names the result should have
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
	return " ".join(names)


#==================================================================================
# Main =
#=======
if __name__ == "__main__":
	parser = argparse.ArgumentParser(description="Letter randomizer.")
	parser.add_argument("--init", help="Drop all current working data and process the next template.", action="store_true")
	parser.add_argument("--random-letter", help="Generate a random letter", action="store_true")
	parser.add_argument("--fill-missing", help="Fill all missing words from database", action="store_true")
	parser.add_argument("--parse-input", help="Parse <input> for words to fill gaps in processed template.", metavar="input")
	#parser.add_argument("--parse-all", help="Parse the contents of templates for database dictionary.", action="store_true") # TODO implement!
	parser.add_argument("--show", help="Shows contents of input.pkl.", action="store_true")
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

	elif args.fill_missing:
		fill_missing()

	elif args.show:
		show_files()

	elif args.random_letter:
		randomize_letter()

	else:
		parser.print_help()




	



