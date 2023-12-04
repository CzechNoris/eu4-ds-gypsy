#!/bin/bash

echo "Which python to use?"
select python in $(ls /opt/homebrew/bin/python* /usr/bin/python* /usr/local/bin/python* /Users/$(whoami)/opt/anaconda3/bin/python* 2>/dev/null); do
    break
done

BUILD_CONFIGS_DIR="data/external/build_configs"
BUILD_CONFIGS=$(ls $BUILD_CONFIGS_DIR)

for BUILD_CONFIG in $BUILD_CONFIGS; do
    echo "Updating $BUILD_CONFIG"
    $python ./scripts/gen_builds.py -b "$BUILD_CONFIGS_DIR/$BUILD_CONFIG" -p 25 --exp-from 5 --exp-top 8000 --exp-rand 30000
done