#!/opt/homebrew/bin/bash

# File meant to create traditional chinese out of simplified chinese
# *.dic files within the IK analyzer plugin

function handle_dics () {
    # Change directory
    command cd ./elasticsearch-analysis-ik-8.3.3/config/
    for f in *.dic
    do
        echo "Processing $f"
        opencc -c s2tw.json -i $f -o /tmp/zhtw-$f
        cp $f /tmp/zhcn-$f
        cat /tmp/zhtw-$f /tmp/zhcn-$f | sort | uniq > $f
    done
}

DIR=/tmp
if [ ! -d "$DIR" ];
then
    command mkdir "$DIR"
fi

if [ -d "./elasticsearch-analysis-ik-8.3.3/config" ]; then
    # If the folder exists, we execute the sctipt
    handle_dics
else
    echo "Cannot process .dic files as folder ${PWD}/elasticsearch-analysis-ik-8.3.3/config doesn't exist!"
fi