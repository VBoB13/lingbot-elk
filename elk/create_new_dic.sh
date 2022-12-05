#!/bin/bash

# File meant to create traditional chinese out of simplified chinese
# *.dic files within the IK analyzer plugin

$FILES = './elasticsearch-analysis-ik-8.3.2/config/*.dic'

for f in $FILES
do
    echo "Processing $f"
    opencc -c s2tw.json -i $f.dic -o /tmp/$f-zhtw.dic
    cp $f.dic /tmp/$f-zhcn.dic
    cat /tmp/$f-zhtw.dic /tmp/$f-zhcn.dic | sort | uniq > $f.dic
done