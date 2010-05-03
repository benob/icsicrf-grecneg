import sys, os, re, binascii, copy
from xml.sax import ContentHandler
from xml.sax import make_parser
import xml.sax
from xml.sax.handler import feature_namespaces, feature_validation

class Reference:
    def __init__(self, parent=None, entity=None, mention=None, semcat="", syncat="", synfunc=""):
        self.parent = parent
        self.entity = entity
        self.mention = mention
        self.semcat = semcat
        self.syncat = syncat
        self.synfunc = synfunc
        self.previous = None
        self.previous_by_entity = None
        self.next = None
        self.next_by_entity = None
        self.manual = None
        self.previous_text = ""
        self.next_text = None
        self.embeds = []
        self.gender = "male"
        self.features = []
    def determine_gender(self, expressions):
        for refex in expressions:
            if refex.text == "she":
                self.gender = "female"
            elif refex.text == "they":
                self.gender = "plural"
    def extract_features(self, tags):
        change = "same"
        if self.previous and self.previous.entity != self.entity:
            change = "different"
        change_synfunc = change + "_" + self.synfunc
        first_time = "new"
        if self.previous_by_entity != None:
            first_time = "known"
        if "," in self.entity:
            all_found = True
            for sub_entity in self.entity.split(","):
                found = False
                previous = self.previous
                while previous:
                    if previous.entity == sub_entity:
                        found = True
                        break
                    previous = previous.previous
                if found == False:
                    all_found = False
                    break
            if all_found:
                first_time = "known"
        begin_paragraph = "continue"
        previous_sent = "no"
        previous_punct = "_"
        previous_word_1gram = "_"
        previous_word_2gram = "_"
        previous_tag = "_"
        if self.previous_text:
            if re.search(r"[!?.]", self.previous_text):
                previous_sent = "yes"
            if "<P>" in self.previous_text:
                begin_paragraph = "begin"
            if re.search(r'[!?.][")\]]?\s*$', self.previous_text):
                previous_punct = "sent"
            elif re.search(r'[;,][")\]]?\s*$', self.previous_text):
                previous_punct = "comma"
            elif re.search(r'[)\]]\s*$', self.previous_text):
                previous_punct = "parenthesis"
            elif re.search(r'"\s*$', self.previous_text):
                previous_punct = "quote"
            words = [x for x in re.split(r'[^a-z0-9]', re.sub('.*[.!?]', '', re.sub(r'\(.*?\)', '', self.previous_text.lower().strip()))) if x != ""]
            tagged_words = []
            for word in words:
                if re.match(r'^\d+$', word):
                    tagged_words.append("CD")
                elif word in tags:
                    tagged_words.append(tags[word])
                else:
                    tagged_words.append("_")
            if len(tagged_words) > 0:
                previous_tag = tagged_words[-1]
            if len(words) > 0: previous_word_1gram = words[-1]
            if len(words) > 1: previous_word_2gram = words[-2] + "_" + words[-1]
        next_sent = "no"
        next_punct = "_"
        next_word_1gram = "_"
        next_word_2gram = "_"
        next_tag = "_"
        if self.next_text:
            if re.search(r"[!?.]", self.next_text):
                next_sent = "yes"
            if re.search(r'^\s*[!?.]', self.next_text):
                next_punct = "sent"
            elif re.search(r'^\s*[;,]', self.next_text):
                next_punct = "comma"
            elif re.search(r'^\s*[(\[]', self.next_text):
                next_punct = "parenthesis"
            elif re.search(r'^\s*"', self.next_text):
                next_punct = "quote"
            words = [x for x in re.split(r'[^a-z0-9]', re.sub('[.!?].*', '', re.sub(r'\(.*?\)', '', self.next_text.lower().strip()))) if x != ""]
            tagged_words = []
            for word in words:
                if re.match(r'^\d+$', word):
                    tagged_words.append("CD")
                elif word in tags:
                    tagged_words.append(tags[word])
                else:
                    tagged_words.append("_")
            while len(tagged_words) > 1 and tagged_words[0] == "RB": tagged_words = tagged_words[1:]
            if len(tagged_words) > 0:
                next_tag = tagged_words[0]
            if len(words) > 0: next_word_1gram = words[0]
            if len(words) > 1: next_word_2gram = words[0] + "_" + words[1]
        previous_gender = "na_"
        if self.previous and change == "different":
            previous_gender = "same"
            if self.previous.gender != self.gender:
                previous_gender = "different"
        embeds_all_known = "_"
        embeds_previous = "_"
        if self.embeds:
            if self.previous and self.previous.entity in self.embeds:
                embeds_previous = "embeds_previous"
            embeds_all_known = "yes"
            for entity in self.embeds:
                found = False
                previous = self.previous
                while previous:
                    if previous.entity == entity:
                        found = True
                        break
                    previous = previous.previous
                if not found:
                    embeds_all_known = "embeds_known"
                    break
        morpho_next = next_word_1gram[:1]
        if len(next_word_1gram) > 1:
            morpho_next = next_word_1gram[:2]
        morpho_previous = previous_word_1gram[:1]
        if len(previous_word_1gram) > 1:
            morpho_previous = previous_word_1gram[:2]
        previous_be = 'no'
        if self.previous_text and re.search(r'\b(was|were|is|are|be)\b[^.?!]*$', self.previous_text): previous_be = 'yes'
        next_be = 'no'
        if self.next_text and re.search(r'^[^\.?!]*\b(was|were|is|are|be)\b', self.next_text): next_be = 'yes'
        #next_tag = "_"
        #if next_word_1gram in tags: next_tag = tags[next_word_1gram]
        #previous_tag = "_"
        #if previous_word_1gram in tags: previous_tag = tags[previous_word_1gram]
        self.features = [
            self.synfunc,
            self.semcat,
            self.syncat,
            change,
            change_synfunc,
            previous_gender,
            first_time,
            begin_paragraph,
            previous_punct,
            next_punct,
            previous_sent,
            next_sent,
            previous_word_1gram.encode("utf-8"),
            previous_word_2gram.encode("utf-8"),
            next_word_1gram.encode("utf-8"),
            next_word_2gram.encode("utf-8"),
            previous_tag,
            next_tag,
            #morpho_next,
            #morpho_previous,
            previous_be,
            next_be,
            embeds_previous,
            embeds_all_known,
        ]

class Expression:
    def __init__(self, parent=None, entity=None, text="", reg08_type="", case=""):
        self.parent = parent
        self.entity = entity
        self.text = text
        self.text_embed = ""
        self.embed_ref = ""
        self.reg08_type = reg08_type
        self.case = case
        self.embeds = []
        self.label = None
        self.banned = False
    def generate_class_label(self, others):
        if self.label != None:
            return
        fullname = None
        for refex in others:
            if refex.reg08_type == "name" and refex.case == "plain" and (fullname == None or len(fullname) < len(refex.text)):
                fullname = refex.text
        labels = []
        labels.append(self.reg08_type)
        labels.append(self.case)
        text = self.text.strip()
        if self.reg08_type == "pronoun":
            if re.search("^(it|he|she|they)( |$)", text):
                labels.append("he")
            elif re.search("^(him|her|them)( |$)", text):
                labels.append("him")
            elif re.search("^who( |$)", text):
                labels.append("who")
            elif re.search("^whose$", text):
                labels.append("whose")
            elif re.search("^whom", text):
                labels.append("whom")
            elif re.search("^(its|his|hers|their)( |$)", text):
                labels.append("his")
            if re.search("that", text):
                labels.append("that")
        if re.search("((him|her|them|it)self(['\xe2]s)?)$", text):
            labels.append("self")
        #if "," in self.text:
        #    labels.append("comma")
        name = ""
        if self.reg08_type == "name" or self.reg08_type == "common":
            name = re.sub(r"\b(him|her|them|it)self\b", "", re.sub(r"['\xe2]s\b", "", text)).strip()
            #if fullname and fullname.lower().startswith(name.lower()) and not fullname.lower().endswith(name.lower()):
            #    labels.append("first")
            #if fullname and fullname.lower().endswith(name.lower()) and not fullname.lower().startswith(name.lower()):
            #    labels.append("family")
            #if re.search(r"\b[A-Z]\.", name):
            #    labels.append("capital")
            name_len = len(text.split(" "))
            if name_len == 1:
                labels.append("short")
            #if name_len > 3:
            #    labels.append("long")
        if self.embeds:
            labels.append("nesting")
        self.label = "_".join(labels)
    def as_xml(self):
        if ":" in self.label:
            return '<REFEX CASE="%s" REG08-TYPE="%s" ENTITY="%s">%s</REFEX>' % (self.case, self.reg08_type, self.entity, self.text_embed)
        else:
            return '<REFEX CASE="%s" REG08-TYPE="%s" ENTITY="%s">%s</REFEX>' % (self.case, self.reg08_type, self.entity, self.text)

class OutputPredictionsHtml(ContentHandler):
    def __init__(self, predictions, expressions, references, filename, output):
        self.predictions = predictions
        self.expressions = expressions
        self.references = references
        self.current = 0
        self.filename = filename
        self.output = output
        self.path = []
        self.last_output = {}
    def startElement(self, name, attr):
        if name == 'REF' and 'REFEX' not in self.path:
            if "ENTITY" not in attr: self.error("ENTITY not found in REF")
            entity = attr["ENTITY"]
            if "MENTION" not in attr: self.error("MENTION not found in REF")
            mention = attr["MENTION"]
            id = '%s:%s:%s' % (self.filename, entity, mention)
            predictions = self.predictions[id]
            max_score = -1
            argmax = []
            list_with_scores = []
            for expression in self.expressions[entity]:
                if expression.banned: continue
                if expression.label in predictions:
                    #print expression.text.encode('utf-8'), expression.label, predictions[expression.label]
                    list_with_scores.append("%s %s %s" % (expression.text.encode('utf-8'), expression.label.encode("utf-8"), predictions[expression.label]))
                    if max_score == predictions[expression.label]:
                        argmax.append(expression)
                    elif max_score < predictions[expression.label]:
                        argmax = [expression]
                        max_score = predictions[expression.label]
                elif max_score == -1:
                    list_with_scores.append("%s %s -1" % (expression.text.encode('utf-8'), expression.label.encode("utf-8")))
                    argmax.append(expression)
                else:
                    list_with_scores.append("%s %s -1" % (expression.text.encode('utf-8'), expression.label.encode("utf-8")))
            selected = 0
            if len(argmax) > 1:
                argmax = sorted(argmax, lambda x, y: cmp(len(y.text), len(x.text)))
                label = argmax[0].label
                if entity not in self.last_output: self.last_output[entity] = {}
                if argmax[0].label not in self.last_output[entity]: self.last_output[entity][label] = 0
                selected = self.last_output[entity][label]
                self.last_output[entity][label] += 1
                self.last_output[entity][label] %= len(argmax)
            if len(argmax[selected].text.split()) > 3:
                argmax[selected].banned = True
            correct = True
            if self.references[self.current].manual and self.references[self.current].manual.text.strip() != argmax[selected].text.strip():
                correct = False
            if not correct: self.output.write('<font color="red" title="%s:%s\n%s">' % (entity.encode("utf-8"), self.references[self.current].manual.text.strip().encode("utf-8"), "\n".join(list_with_scores)))
            self.output.write("[%s:%s]" % (entity.encode("utf-8"), argmax[selected].text.encode('utf-8')))
            if not correct: self.output.write('</font>')
            self.current += 1
        self.path.append(name)
    def endElement(self, name):
        self.path.pop()
    def characters(self, chars):
        if 'PARAGRAPH' in self.path and 'REF' not in self.path:
            self.output.write(chars.replace("&", "&amp;").encode("utf-8"))

class OutputPredictions(ContentHandler):
    def __init__(self, predictions, expressions, filename, output):
        self.predictions = predictions
        self.expressions = expressions
        self.filename = filename
        self.output = output
        self.output.write('<?xml version="1.0" encoding="utf-8"?>\n')
        self.output.write('<!DOCTYPE GREC-ITEM SYSTEM "genchal09-grec.dtd">\n')
        self.path = []
        self.last_output = {}
    def startElement(self, name, attr):
        if name == 'REF' and 'REFEX' not in self.path:
            if "ENTITY" not in attr: self.error("ENTITY not found in REF")
            entity = attr["ENTITY"]
            if "MENTION" not in attr: self.error("MENTION not found in REF")
            mention = attr["MENTION"]
            id = '%s:%s:%s' % (self.filename, entity, mention)
            predictions = self.predictions[id]
            max_score = -1
            argmax = []
            for expression in self.expressions[entity]:
                if expression.banned:
                    continue
                if expression.label in predictions:
                    #print expression.text.encode('utf-8'), expression.label, predictions[expression.label]
                    if max_score == predictions[expression.label]:
                        argmax.append(expression)
                    elif max_score < predictions[expression.label]:
                        argmax = [expression]
                        max_score = predictions[expression.label]
                elif max_score == -1:
                    argmax.append(expression)
            attributes = ' '.join(['%s="%s"' % (x, y) for x, y in attr.items()])
            if attributes != '': attributes = ' ' + attributes
            self.output.write(("<%s%s>" % (name, attributes)).encode("utf-8"))
            selected = 0
            if len(argmax) > 1:
                argmax = sorted(argmax, lambda x, y: cmp(len(y.text), len(x.text)))
                label = argmax[0].label
                if entity not in self.last_output: self.last_output[entity] = {}
                if argmax[0].label not in self.last_output[entity]: self.last_output[entity][label] = 0
                selected = self.last_output[entity][label]
                self.last_output[entity][label] += 1
                self.last_output[entity][label] %= len(argmax)
            if len(argmax[selected].text.split()) > 3:
                argmax[selected].banned = True
            self.output.write(argmax[selected].as_xml().encode('utf-8'))
        elif 'REF' not in self.path:
            attributes = ' '.join(['%s="%s"' % (x, y) for x, y in attr.items()])
            if attributes != '': attributes = ' ' + attributes
            self.output.write(("<%s%s>" % (name, attributes)).encode("utf-8"))
        self.path.append(name)
    def endElement(self, name):
        if 'REF' not in self.path[:-1] or 'ALT-REFEX' in self.path:
            self.output.write(("</%s>" % name).encode("utf-8"))
        self.path.pop()
    def characters(self, chars):
        if 'REF' not in self.path:
            self.output.write(chars.replace("&", "&amp;").encode("utf-8"))
        
class ExtractFeatures(ContentHandler):
    def __init__(self):
        self.current = None
        self.current_refex = None
        self.previous = None
        self.entities = {}
        self.expressions = {}
        self.references = []
        self.path = []
        self.ref_text = ""
        self.text = ""
    def startElement(self, name, attr):
        if name == "REF":
            if "ENTITY" not in attr: self.error("ENTITY not found in REF")
            entity = attr["ENTITY"]
            if "ALT-REFEX" in self.path:
                self.current_refex.text += " <%s> " % entity
                self.current_refex.embeds.append(entity)
                self.current_refex.embed_ref += " <REF %s><%s></REF> " % (" ".join(['%s="%s"' % (x, y) for x, y in attr.items()]), entity)
            else:
                if "MENTION" not in attr: self.error("MENTION not found in REF")
                mention = attr["MENTION"]
                if "SEMCAT" not in attr: self.error("SEMCAT not found in REF")
                semcat = attr["SEMCAT"]
                if "SYNCAT" not in attr: self.error("SYNCAT not found in REF")
                syncat = attr["SYNCAT"]
                if "SYNFUNC" not in attr: self.error("SYNFUNC not found in REF")
                synfunc = attr["SYNFUNC"]
                ref = Reference(parent=self.current, mention=mention, entity=entity, semcat=semcat, syncat=syncat, synfunc=synfunc)
                self.current = ref
                if entity not in self.entities:
                    self.entities[entity] = []
                    ref.previous_by_entity = None
                else:
                    ref.previous_by_entity = self.entities[entity][-1]
                    self.entities[entity][-1].next_by_entity = ref
                self.entities[entity].append(ref)
                ref.previous = self.previous
                if self.previous != None:
                    self.previous.next = ref
                if "REFEX" not in self.path:
                    ref.previous_text = self.cleanup(self.ref_text)
                    if self.previous != None and self.previous.next_text == None:
                        self.previous.next_text = ref.previous_text
                    self.previous = ref
                    self.references.append(ref)
                    self.ref_text = ""
                self.text += "["
        elif name == "REFEX":
            if "ENTITY" not in attr: self.error("ENTITY not found in REFEX")
            entity = attr["ENTITY"]
            if "REG08-TYPE" not in attr: self.error("REG08-TYPE not found in REFEX")
            reg08_type = attr["REG08-TYPE"]
            if "CASE" not in attr: self.error("CASE not found in REFEX")
            case = attr["CASE"]
            refex = Expression(parent=self.current_refex, entity=entity, reg08_type=reg08_type, case=case)
            self.current_refex = refex
            if self.current != None and len(self.path) > 0 and self.path[-1] == "REF":
                self.current.manual = refex
            if "ALT-REFEX" in self.path:
                if entity not in self.expressions:
                    self.expressions[entity] = []
                self.expressions[entity].append(refex)
        self.path.append(name)
    def endElement(self, name):
        if name == "REF":
            if "ALT-REFEX" not in self.path:
                self.current = self.current.parent
                self.text += "]"
        elif name == "REFEX":
            if self.current_refex.parent != None:
                self.current_refex.parent.text += self.current_refex.text
                self.current.parent.embeds.append(self.current)
            self.current_refex.text = self.cleanup(self.current_refex.text)
            self.current_refex = self.current_refex.parent
        elif name == "PARAGRAPH":
            self.text += "<BR>"
            if len(self.references) > 0:
                self.references[-1].next_text = self.cleanup(self.ref_text + "</P>")
            self.ref_text = "<P> "
        self.path.pop()
    def characters(self, chars):
        if self.current_refex != None and len(self.path) > 0 and self.path[-1] == "REFEX":
            self.current_refex.text += chars
            self.current_refex.embed_ref += chars
        if "PARAGRAPH" in self.path:
            self.text += chars
        if "PARAGRAPH" in self.path and "REF" not in self.path:
            self.ref_text += chars
    def error(self, exception):
        sys.stderr.write('ERROR: %s\n' % exception)
    def cleanup(self, text):
        text = re.sub(r"[\n\r\s]+", " ", text)
        text = re.sub(r"\[ ", "[", text)
        text = re.sub(r" \]", "]", text)
        text = re.sub(r"\s*<BR>\s*", "\n", text)
        return text.strip()
    def generate_class_labels(self):
        for entity in sorted(self.expressions):
            for refex in sorted(self.expressions[entity], lambda x, y: cmp(x.text, y.text)):
                refex.generate_class_label(self.expressions[entity])
        for ref in self.references:
            if ref.manual:
                ref.manual.generate_class_label(self.expressions[entity])
    def display(self):
        #print self.cleanup(self.text).encode("utf-8")
        #for ref in self.references:
        #    pass
            #print ref.previous_text.encode("utf-8"), "[%s]" % ref.manual.text.strip().encode("utf-8"), ref.next_text.encode("utf-8")
            #print "[%s]" % ref.manual.text.strip().encode("utf-8")
            #if ref.embeds != None:
            #    print "<%s>" % ref.embeds.entity
        for entity in sorted(self.entities):
            print entity
            #print entity, str([x.manual.text.strip().encode("utf-8") for x in self.entities[entity] if x.manual != None])
            for refex in sorted(self.expressions[entity], lambda x, y: cmp(x.text, y.text)):
                print "  " + refex.text.strip().encode("utf-8") + " " + refex.label

    def generate_embedded(self, expression=None, path=[]):
        if expression != None:
            output = []
            for entity in expression.embeds:
                if entity in path: continue # prevent loops
                path.append(entity)
                for entity_refex in self.expressions[entity]:
                    if entity_refex.embeds:
                        for refex in self.generate_embedded(entity_refex):
                            text = expression.text.replace("<%s>" % entity, refex.text)
                            new_refex = copy.copy(expression)
                            new_refex.text = text
                            new_refex.label = refex.label + ":" + expression.label
                            new_refex.text_embed = expression.embed_ref.replace("<%s>" % entity,
                                '<REFEX REG08-TYPE="%s" CASE="%s">%s</REFEX>' 
                                % (refex.reg08_type, refex.case, refex.text))
                            if expression.text.startswith("<"):new_refex.label += "_left"
                            if expression.text.endswith(">"):new_refex.label += "_right"
                            output.append(new_refex)
                    else:
                        text = expression.text.replace("<%s>" % entity, entity_refex.text)
                        new_refex = copy.copy(expression)
                        new_refex.text = text
                        new_refex.label = entity_refex.label + ":" + expression.label
                        new_refex.text_embed = expression.embed_ref.replace("<%s>" % entity,
                            '<REFEX REG08-TYPE="%s" CASE="%s">%s</REFEX>' 
                            % (entity_refex.reg08_type, entity_refex.case, entity_refex.text))
                        if expression.text.startswith("<"):new_refex.label += "_left"
                        if expression.text.endswith(">"):new_refex.label += "_right"
                        output.append(new_refex)
                path.pop()
            return output
        else:
            generated = {}
            for entity in self.expressions:
                generated[entity] = []
                for expression in self.expressions[entity]:
                    if expression.embeds:
                        generated[entity].extend(self.generate_embedded(expression))
                    else:
                        generated[entity].append(expression)
            self.expressions = generated

    def extract_features(self, filename, tags=None):
        for entity in self.entities:
            for ref in self.entities[entity]:
                ref.determine_gender(self.expressions[ref.entity])
                ref.extract_features(tags)
        for entity in self.entities:
            for ref in self.entities[entity]:
                features = [x for x in ref.features]
                #if ref.previous:# and ref.previous.entity != ref.entity:
                #    features.extend(ref.previous.features)
                #else:
                #    features.extend(["?" for x in ref.features])
                if ref.manual:
                    ref.manual.generate_class_label(self.expressions[ref.entity])
                    for peer in self.expressions[ref.entity]: # assumes recursions are already removed
                        if peer.text.lower().strip() == ref.manual.text.lower().strip():
                            ref.manual.label = peer.label
                    print filename + ":%s:%s " % (ref.entity, ref.mention) + " ".join(features) + " " + ref.manual.label #+ " " + ref.manual.text
                else:
                    print filename + ":%s:%s " % (ref.entity, ref.mention) +" ".join(features)
            print
    
def process_file(filename, handler):
    parser = make_parser()
    content = []
    fp = open(filename)
    for line in fp:
        if not line.startswith("<!DOCTYPE"): # disable DTD as it's not in the directory
            content.append(line)
    fp.close()
    xml.sax.parseString("".join(content), handler)
    return handler

if __name__ == '__main__':
    if len(sys.argv) < 2 or not (sys.argv[1] == "-t" or sys.argv[1] == "-p" or sys.argv[1] == '-h'):
        sys.stderr.write('USAGE: %s <option> files\n  Generate training data: -t files\n  Process predictions: -p <output_dir> files < predictions\n' % (sys.argv[0]))
        sys.exit(1)
    if sys.argv[1] == "-t":
        tags = {}
        for line in open("lex150k.en"):
            tokens = line.strip().split()
            max = 0
            argmax = None
            for i in xrange(2, len(tokens), 3):
                if int(tokens[i]) > max or argmax == None:
                    max = int(tokens[i])
                    argmax = tokens[i - 1]
            tags[tokens[0]] = argmax
        for filename in sys.argv[2:]:
            handler = process_file(filename, ExtractFeatures())
            handler.generate_class_labels()
            handler.generate_embedded() # requires class labels
            handler.extract_features(binascii.hexlify(filename), tags) # interpreting utf-8 filenames is somewhat weird, so encode it as hexa
            #handler.display()
    elif sys.argv[1] == '-p':
        predictions = {}
        for line in sys.stdin:
            tokens = line.strip().split()
            if len(tokens) > 5:
                id = tokens[0]
                predictions[id] = {}
                while re.search(r'/[0-9.]+$', tokens[-1]):
                    label, score = tokens[-1].split("/")
                    predictions[id][label] = float(score)
                    tokens.pop()
        output_dir = sys.argv[2]
        for filename in sys.argv[3:]:
            handler = process_file(filename, ExtractFeatures())
            handler.generate_class_labels()
            handler.generate_embedded()
            output_file = output_dir + "/" + "/".join(filename.split("/")[-2:])
            os.system("mkdir -p `dirname \"%s\"`" % output_file)
            output_fp = open(output_file, "w")
            process_file(filename, OutputPredictions(predictions, handler.expressions, binascii.hexlify(filename), output_fp))
            output_fp.close()
    elif sys.argv[1] == '-h': # generate html for debug
        predictions = {}
        for line in sys.stdin:
            tokens = line.strip().split()
            if len(tokens) > 5:
                id = tokens[0]
                predictions[id] = {}
                while re.search(r'/[0-9.]+$', tokens[-1]):
                    label, score = tokens[-1].split("/")
                    predictions[id][label] = float(score)
                    tokens.pop()
        print '<html><head><meta http-equiv="Content-Type" content="text/html; charset=UTF-8"></head><body>'
        for filename in sys.argv[2:]:
            handler = process_file(filename, ExtractFeatures())
            handler.generate_class_labels()
            handler.generate_embedded()
            process_file(filename, OutputPredictionsHtml(predictions, handler.expressions, handler.references, binascii.hexlify(filename), sys.stdout))
            print "<hr>"
        print "</body></html>"

