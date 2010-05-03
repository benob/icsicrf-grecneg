#!/usr/bin/env python2.5

from lxml import etree
#from grec_msr09_from_crf_v1.py import get_classes
import sys
import re
import binascii
import os

def load_conll_features(filename):
    conll_features = {}
    sentence = []
    for line in open(filename).readlines():
        line = line.strip()
        if line != "":
            sentence.append(line.split("\t"))
        else:
            for i in range(len(sentence)):
                if sentence[i][2].startswith("REF"):
                    id = sentence[i][2].split(" ")[1]
                    features = []
                    # extract pos tags
                    pos_tag = []
                    for j in range(1, 0, -1):
                        if i - j >= 0:
                            pos_tag.append(sentence[i - j][3])
                        else:
                            pos_tag.append("?")
                    for j in range(1, 2):
                        if i + j < len(sentence):
                            pos_tag.append(sentence[i + j][3])
                        else:
                            pos_tag.append("?")
                    pos_tag.append("_".join(pos_tag[0:3]))
                    pos_tag.append("_".join(pos_tag[1:3]))
                    pos_tag.append("_".join(pos_tag[0:2]))
                    pos_tag.append("_".join(pos_tag[3:5]))
                    pos_tag.append("_".join(pos_tag[3:6]))
                    pos_tag.append("_".join(pos_tag[4:6]))
                    pos_tag = ["?" if "?" in x else x for x in pos_tag]
                    features.extend(pos_tag)
                    #parent_tag = sentence[int(sentence[i][8]) - 1][3]
                    #features.append(parent_tag)
                    conll_features[id] = features
            sentence = []
    return conll_features

def process_file(filename):
    prev_entity = ""
    prev_prev_features = None
    prev_features = None
    seen_entity = {}
    since_last_change = {}
    prev_entity_features = {}
    candidates = {}
    full_name = {}
    root = etree.parse(filename).getroot()
    directory = filename.split("/")[-2]
    conll = re.sub("\.xml$", ".conll09", filename)
    conll_features = None
    #if os.path.exists(conll):
    #    conll_features = load_conll_features(conll)
    for par in root.findall(".//PARAGRAPH"):
        begin_paragraph = "begin_par"
        for ref in par.findall(".//REF"):
            refex = ref.findall("REFEX")
            if len(refex) > 0:
                entity = "n/a"
                if "ENTITY" in ref.attrib:
                    entity = ref.attrib["ENTITY"]
                if entity != "n/a":
                    id = binascii.hexlify(filename) + ":" + entity + ":" + ref.attrib["MENTION"] # unique id
                else:
                    id = binascii.hexlify(filename) + ":" + ref.attrib["ID"] # unique id

                # get class label
                classes = []
                for attribute in ("CASE", "REG08-TYPE", "HEAD", "EMPHATIC"):
                    if attribute in refex[0].attrib:
                        classes.append(refex[0].attrib[attribute])

                if ref.attrib["SEMCAT"] == "person":
                    # get possible outputs for this example (not used yet)
                    if entity not in full_name:
                        all_possibles = []
                        if entity != "n/a":
                            all_possibles = root.findall(".//ALT-REFEX/REFEX[@ENTITY='"+entity+"']")
                        else:
                            all_possibles = ref.findall(".//ALT-REFEX/REFEX")
                        for possible in all_possibles:
                            if not possible.text: continue
                            name = possible.text
                            name = re.sub("((him|her|them|it)self|['\xe2]s)$", "", name)
                            if re.search("^[A-Z].*[A-Z][^A-Z ]+$", name):
                                if entity not in full_name:
                                    full_name[entity] = []
                                full_name[entity].append(name)
                        if entity in full_name:
                            full_name[entity].sort(lambda x, y: len(y) - len(x))
                            full_name[entity] = full_name[entity][0]

                    # characterize class with extra attributes
                    text = re.sub("</REFEX>[\r\n]*$", "", re.sub(r"^<REFEX [^>]*>", "", etree.tostring(refex[0]))).lower()
                    if "REG08-TYPE" in refex[0].attrib and refex[0].attrib["REG08-TYPE"] == "pronoun":
                        if re.search("^(it|he|she|they)( |$)", text):
                            classes.append("he")
                        elif re.search("^(him|her|them)( |$)", text):
                            classes.append("him")
                        elif re.search("^who( |$)", text):
                            classes.append("who")
                        elif re.search("^whose$", text):
                            classes.append("whose")
                        elif re.search("^whom", text):
                            classes.append("whom")
                        elif re.search("^(its|his|hers|their)( |$)", text):
                            classes.append("his")
                        if re.search("that", text):
                            classes.append("that")
                        if re.search("self$", text):
                            classes.append("self")
                    if "REG08-TYPE" in refex[0].attrib and refex[0].attrib["REG08-TYPE"] == "name":
                        if "," in text:
                            classes.append("comma")
                        if entity in full_name:
                            name = re.sub("((him|her|them|it)self|['\xe2]s)$", "", text)
                            if full_name[entity].lower().endswith(name.lower()) and len(name) < len(full_name[entity]):
                                classes.append("family")
                            if full_name[entity].lower().startswith(name.lower()) and len(name) < len(full_name[entity]):
                                classes.append("first")
                        else:
                            name_len = len(text.split(" "))
                            if name_len == 1:
                                classes.append("short")
                            elif name_len > 3:
                                classes.append("long")
                # =========== extract features ================
                # generate previous/next punctuation and words
                previous_punct = "none"
                previous = ref.getprevious()
                previous_words = ()
                if previous != None:
                    previous_words = re.sub("[^a-z]", " ", previous.tail.lower()).split()
                    if re.search(r'[\.!?]\s+$', previous.tail):
                        previous_punct = "sent"
                    elif previous.tail.endswith(", \n"):
                        previous_punct = "comma"
                    elif previous.tail.endswith(") \n"):
                        previous_punct = "parenthesis"
                else:
                    previous_punct = "sent"
                next_punct = "none"
                if ref.tail != "":
                    if re.search(r'^\s+[\.!?]', ref.tail):
                        next_punct = "sent"
                    elif ref.tail.startswith("\n ,"):
                        next_punct = "comma"
                    elif ref.tail.startswith("\n ("):
                        next_punct = "parenthesis"
                next_words = re.sub("[^a-z]", " ", ref.tail.lower()).split()

                # get synfunc, semcat, syncat
                synfunc = "?"
                if "SYNFUNC" in ref.attrib:
                    synfunc = ref.attrib["SYNFUNC"]
                syncat = ref.attrib["SYNCAT"]
                semcat = ref.attrib["SEMCAT"]
                #synfunc = synfunc.replace("-", " ")

                # change in entity
                change = "no_change"
                if entity != prev_entity:
                    change = "change"
                    since_last_change[entity] = 0

                # number of times entity was seen
                if entity not in seen_entity: seen_entity[entity] = 0
                else: seen_entity[entity] += 1
                if seen_entity[entity] > 3: seen_entity[entity] = 3

                # number of times entity was seen consecutivelly
                if entity not in since_last_change: since_last_change[entity] = 0
                else: since_last_change[entity] += 1
                if since_last_change[entity] > 3: since_last_change[entity] = 3

                # word ngrams after the entity
                next_words_1gram = "?"
                if len(next_words) >= 1:
                    next_words_1gram = "_".join(next_words[:1])
                next_words_2gram = "?"
                if len(next_words) >= 2:
                    next_words_2gram = "_".join(next_words[:2])
                next_words_3gram = "?"
                if len(next_words) >= 3:
                    next_words_3gram = "_".join(next_words[:3])

                # word ngrams before the entity
                previous_words_1gram = "?"
                if len(previous_words) >= 1:
                    previous_words_1gram = "_".join(previous_words[-1:])
                previous_words_2gram = "?"
                if len(previous_words) >= 2:
                    previous_words_2gram = "_".join(previous_words[-2:])
                previous_words_3gram = "?"
                if len(previous_words) >= 3:
                    previous_words_3gram = "_".join(previous_words[-3:])

                # previous morph
                previous_morph = "_"
                if previous_words_1gram.endswith("ing"):
                    previous_morph = "ing"
                if previous_words_1gram.endswith("ed"):
                    previous_morph = "ed"
                if previous_words_1gram.endswith("s"):
                    previous_morph = "s"

                # next morph
                next_morph = "_"
                if next_words_1gram.endswith("ing"):
                    next_morph = "ing"
                if next_words_1gram.endswith("ed"):
                    next_morph = "ed"
                if next_words_1gram.endswith("s"):
                    next_morph = "s"

                # features of current entity
                features = [
                    synfunc,
                    semcat,
                    syncat,
                    #directory,
                    change,
                    str(seen_entity[entity]),
                    str(since_last_change[entity]), 
                    begin_paragraph,
                    previous_punct,
                    next_punct,
                    previous_words_1gram,
                    previous_words_2gram,
                    #previous_words_3gram,
                    next_words_1gram,
                    next_words_2gram,
                    #next_words_3gram,
                ]

                if conll_features != None:
                    if not ref.attrib["ID"] in conll_features:
                        sys.stderr.write("ERROR: no conll09 features for [" + filename + ":" + ref.attrib["ID"] + "] skipping file\n")
                        return
                        #sys.exit(1)
                    else:
                        features.extend(conll_features[ref.attrib["ID"]])

                # setup features from previous entity and previous occurrence of the same entity
                if entity not in prev_entity_features:
                    prev_entity_features[entity] = ['?' for i in range(len(features))]
                if prev_features == None:
                    prev_features = ['?' for i in range(len(features))]
                if prev_prev_features == None:
                    prev_prev_features = ['?' for i in range(len(features))]

                # generate output
                output = []
                output.extend(features)
                output.extend(prev_features)
                if entity != "n/a":
                    output.extend(prev_entity_features[entity])
                else:
                    output.extend(prev_prev_features)

                # print output
                print id + "\t" + "\t".join(output) + "\t" + "_".join(classes)

                # set previous stuff
                prev_prev_features = prev_features
                prev_features = features
                prev_entity_features[entity] = features
                prev_entity = entity

            begin_paragraph = "in_par"
    print

for file in sys.argv[1:]:
    process_file(file)
