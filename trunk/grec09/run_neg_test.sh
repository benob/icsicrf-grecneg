#!/bin/bash
export PYTHONPATH=$HOME/install/lib/python2.5/site-packages/:$HOME/install2/lxml-2.1.5/build/lib.linux-i686-2.5/:$HOME/install2/lib/python2.3/site-packages/
export LD_LIBRARY_PATH=$HOME/install2/lib
STEM=grec_neg
./grec_msr09_to_crf_v1.py GREC-NEG-09/Training-Data/train/*/*.xml | ./convert_unknown_to_ignore.pl > $STEM.crf.data 
./generate-crf-template-2.pl `head -1 $STEM.crf.data | awk '{print NF}'` > $STEM.crf.template
c=1
#/u/favre/install/CRF++-0.51/crf_learn -c $c -t -f 5 $STEM.crf.template $STEM.crf.data $STEM.crf.model.$c.new

rm -rf output_neg output_neg2

#./grec_msr09_to_crf_v1.py GREC-NEG-09/Training-Data/dev/*/*.xml \
./grec_msr09_to_crf_v1.py GREC-NEG-09_TEST_DATA/*/*.xml \
    | /u/favre/install/CRF++-0.51/crf_test -v 2 -m $STEM.crf.model.$c.new \
    | ./grec_msr09_from_crf_v1.py output_neg

while [ `grep '"?"' $(find output_neg -name '*.xml') | grep 'xRESOLVED="no"' | cut -f1 -d: | sort -u | wc -l` != 0 ]
do
    ./grec_msr09_to_crf_v1.py `grep '"?"' $(find output_neg -name '*.xml') | grep 'xRESOLVED="no"' | cut -f1 -d: | sort -u` \
        | /u/favre/install/CRF++-0.51/crf_test -v 2 -m $STEM.crf.model.$c.new \
        | ./grec_msr09_from_crf_v1.py output_neg2
    for i in output_neg2/*/*.xml; do cp $i `echo $i | sed 's/output_neg2/output_neg/'`; done
done

#for c in `seq 0.01 0.01 0.1`
#do
#echo "/u/favre/install/CRF++-0.51/crf_learn -c $c -t -f 5 $STEM.crf.template $STEM.crf.data $STEM.crf.model.$c"
#done > run-command.list
#run-command -J 12 -f run-command.list

#mkdir -p perf2
#for c in `seq 0.01 0.01 0.1`
#do
#rm -rf output2
#/u/favre/install/CRF++-0.51/crf_test -v 2 -m $STEM.crf.model.$c $STEM.crf.dev | ./grec_msr09_from_crf_v1_output2.py > /dev/null
cd geval
./geval-2.1.pl ../GREC-NEG-09/Training-Data/dev ../output_neg #| tee ../perf2/$c
cd ..
#done
