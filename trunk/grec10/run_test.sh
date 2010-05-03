#!/bin/bash

# create datasets
python grec_to_crf.py -t ../Training-Data/train/*/*.xml > neg10_new.train
python grec_to_crf.py -t ../Training-Data/dev/*/*.xml > neg10_new.dev
python grec_to_crf.py -t ../GREC-NEG-10_TEST_DATA/*/*.xml > neg10_new.test
cat neg10_new.train neg10_new.dev > neg10_new.train+dev
perl generate_template.pl `head -1 neg10_new.train | awk '{print NF}'` > neg10_new.template

# process dev
crf_learn -c 0.07 -f 5 neg10_new.template neg10_new.train neg10_new.model
crf_test -v 2 -m neg10_new.model neg10_new.dev | python grec_to_crf.py -p output.dev/ ../Training-Data/dev/*/*.xml

# process test
crf_learn -c 0.07 -f 5 neg10_new.template neg10_new.train+dev neg10_new.model+dev
crf_test -v 2 -m neg10_new.model+dev neg10_new.test | python grec_to_crf.py -p output.test/ ../GREC-NEG-10_TEST_DATA/*/*.xml

# evaluate on dev
crf_test -m neg10_new.model neg10_new.dev | awk '/./{if($NF==$(NF-1)){ok++}n++}END{print ok,n,ok/n}'
../Evaluation-Software/geval.pl ../Training-Data/dev/ output.dev/
