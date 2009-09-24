#!/usr/bin/env python2.5

from lxml import etree
import sys
import re
import binascii
import os
import random

def get_classes(node, type):
    candidates = {}
    full_name = {}
    all_possibles = node.findall(".//ALT-REFEX/REFEX")
    # determine full names for persons
    for possible in all_possibles:
        entity = "n/a";
        if "ENTITY" in possible.attrib:
            entity = possible.attrib["ENTITY"]
        if not possible.text: continue
        name = possible.text
        name = re.sub("['\xe2]s$", "", name)
        if re.search("^[A-Z].*[A-Z][^A-Z ]+$", name):
            if entity not in full_name:
                full_name[entity] = []
            full_name[entity].append(name)
    for entity in full_name:
        full_name[entity].sort(lambda x, y: len(y) - len(x))
        full_name[entity] = full_name[entity][0]
    # generate class ids
    for possible in all_possibles:
        classes = []
        for attribute in ("CASE", "REG08-TYPE", "HEAD", "EMPHATIC"):
            if attribute in possible.attrib:
                classes.append(possible.attrib[attribute])

        entity = "n/a";
        if "ENTITY" in possible.attrib:
            entity = possible.attrib["ENTITY"]

        if type == "person":
            # characterize class with extra attributes
            text = re.sub("</REFEX>[\r\n]*$", "", re.sub(r"^<REFEX [^>]*>", "", etree.tostring(possible)))
            if "REG08-TYPE" in possible.attrib and possible.attrib["REG08-TYPE"] == "pronoun":
                if re.search("^(it|he|she|they)( |$)", text):
                    classes.append("he")
                elif re.search("^(its|him|her|them)( |$)", text):
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
            if "REG08-TYPE" in possible.attrib and possible.attrib["REG08-TYPE"] == "name":
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
        if len(possible.findall(".//REF")) > 0:
            classes.append("nested")
        if entity not in candidates:
            candidates[entity] = {}
        tag = "_".join(classes)
        possible.attrib["TAG"] = tag
        if tag not in candidates[entity]:
            candidates[entity][tag] = []
        candidates[entity][tag].append(possible)
        #candidates[entity][tag].sort(lambda x, y: len(y.text) - len(x.text))
    return candidates

def process_file(output_dir, filename, predictions):
    #root = etree.parse(filename.replace("dev","dev2")).getroot()
    root = etree.parse(filename).getroot()
    candidates = {}

    if len(root.findall("./ALT-REFEX/")) > 0:
        candidates = get_classes(root, "person")

    for par in root.findall(".//PARAGRAPH"):
        begin_paragraph = "begin_par"
        found_refs = par.findall(".//REF")
        found_refs.reverse()
        for ref in found_refs:
            entity = "n/a"
            if "ENTITY" in ref.attrib:
                entity = ref.attrib["ENTITY"]
            if entity != "n/a":
                id = binascii.hexlify(filename) + ":" + entity + ":" + ref.attrib["MENTION"] # unique id
            else:
                id = binascii.hexlify(filename) + ":" + ref.attrib["ID"] # unique id

            if id not in predictions:
                sys.stderr.write("ERROR: prediction not found for [" + filename + ":" + id + "]\n")
                sys.exit(1)

            # this is a nested prediction
            refex = ref.findall("REFEX")
            has_nested = 0
            if len(ref.findall(".//REF")) > 0:
                #ref.attrib["HAS_NESTED"] = "yes"
                has_nested = 1
                predictions[id] = [x + "_nested" for x in predictions[id]]
                #ref.attrib["ALL_PRED"] = repr(predictions[id])
            else:
                if len(refex) > 0:
                    ref.remove(refex[0]) # supposedly before anything else
            prediction = predictions[id][0]
            text = ""

            if len(ref.findall("./ALT-REFEX")) > 0:
                candidates = get_classes(ref, ref.attrib["SEMCAT"])

            i = 0
            if entity in candidates:
                while prediction not in candidates[entity] and i < len(predictions[id]):
                    prediction = predictions[id][i]
                    i += 1
                #chosen = random.randint(0, len(candidates[entity][prediction]) - 1)
                chosen = -1
                if i >= len(predictions[id]):
                    sys.stderr.write("ERROR: predictions " + repr(predictions[id]) 
                            + " not found in " + repr(candidates[entity].keys()) + "\n")
                    sys.exit(1)
                ref.attrib["PREDICTION"] = prediction
                ref.attrib["CHOICE"] = str(len(candidates[entity][prediction]))
                text = etree.tostring(candidates[entity][prediction][chosen]) 
                #if re.search("<REF ", text):
                if has_nested:
                    #ref.attrib["NESTED"] = "yes"
                    nested = ref.findall(".//REF")
                    if len(nested) > 0:
                        nested[0].tail = ""
                        text = re.sub("<REF[^>]*/>", " " + etree.tostring(nested[0]) + " ", text)
                    ref.text = ""
                    if len(refex) > 0:
                        ref.remove(refex[0])
                    if nested[0].getparent() == ref:
                        #nested[0].remove(list(nested[0])[0])
                        ref.remove(nested[0])

            new_refex = etree.XML(text)
            new_refex.attrib["NEW"] = "yes"
            new_refex.tail = "\n"
            ref.insert(0, new_refex)
    output_file = output_dir + "/" + "/".join(filename.split("/")[-2:])
    if not os.path.exists(output_dir + "/" + filename.split("/")[-2]):
        os.mkdir(output_dir + "/" + filename.split("/")[-2])
    output = open(output_file, "w")
    print output_file
    etree.ElementTree(root).write(output, encoding="utf-8")
    output.close()

READ_POSTERIORS = 1
predictions = {}
output_dir = "output"
if not os.path.exists(output_dir):
    os.mkdir(output_dir)

for line in sys.stdin.readlines():
    if line.startswith("#"): continue
    fields = line.split()
    if len(fields) > 5:
        if READ_POSTERIORS == 1:
            predictions[fields[0]] = []
            i = 1
            while "/" in fields[-i]:
                predictions[fields[0]].append(fields[-i])
                i += 1
            predictions[fields[0]].pop()
            predictions[fields[0]].sort(lambda x, y: cmp(float(y.split("/")[1]), float(x.split("/")[1])))
            predictions[fields[0]] = [x.split("/")[0] for x in predictions[fields[0]]]
        else:
            predictions[fields[0]] = [fields[-1]]
    else:
        filename = predictions.keys()[0].split(":")[0]
        filename = binascii.unhexlify(filename)
        process_file(output_dir, filename, predictions)
        predictions = {}
