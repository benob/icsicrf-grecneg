#!/usr/bin/env python2.5
from lxml import etree
import math
import re
import sys

print '<html><head><meta http-equiv="Content-Type" content="text/html; charset=UTF-8"></head><body>'

for filename in sys.argv[1:]:
    print "<hr>"
    print "<h3>" + filename + "</h3>"
    root = etree.parse(filename).getroot()
    for par in root.findall(".//PARAGRAPH"):
        print "<p>"
        print par.text.encode('UTF-8')
        for child in par:
            #print "<select>"
            correct = child.findall('./REFEX')[0]
            options = child.findall('./ALT-REFEX/REFEX')
            if len(options) == 0:
                options = root.findall("./ALT-REFEX/REFEX[@ENTITY='"+child.attrib['ENTITY']+"']")
            for option in options:
                if "xSCORE" not in option.attrib:
                    option.attrib["xSCORE"] = "-1"
            options.sort(lambda y, x: cmp(float(x.attrib["xSCORE"]), float(y.attrib["xSCORE"])))
            score_max = float(options[0].attrib["xSCORE"])
            for option in options:
                color = "white"
                fgcolor = "black"
                selected = ""
                marker = ""
                score = float(option.attrib["xSCORE"])
                value = (255 - int(score / score_max * 256))
                is_hyp = 1
                if option.text == None:
                    print "<option> EMBEDED </option>"
                    continue
                if correct.text != None and option.text.lower() != correct.text.lower():
                    is_hyp = 0
                for attrib in correct.attrib:
                    if attrib not in option:
                        continue
                    if correct.attrib[attrib] != option.attrib[attrib]:
                        is_hyp = 0
                        break
                if is_hyp:
                    selected = "selected"
                    if "xISREFTEXT" in option.attrib:
                        color = "green"
                    else:
                        color = "red"
                if score == -1:
                    color = "dddddd"
                if option.attrib["xTAG"] == correct.attrib["xTAG"]:
                    fgcolor = "blue"
                if "xISREFTEXT" in option.attrib:
                    marker += "*"
                if not is_hyp: continue
                print "<b><font color=\"" + color + "\">" + option.text.encode('UTF-8') + "</font></b>"
            print child.tail.encode('UTF-8')
        print "</p>"
print "</body></html>"

