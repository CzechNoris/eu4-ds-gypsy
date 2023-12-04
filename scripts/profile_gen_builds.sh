#!/bin/bash

echo "Which python to use?"
select python in $(ls /opt/homebrew/bin/python* /usr/bin/python* /usr/local/bin/python* /Users/$(whoami)/opt/anaconda3/bin/python* 2>/dev/null); do
    break
done

$python -m cProfile -o output/cprofiler -s cumtime ./scripts/gen_builds.py -b data/external/build_configs/_build_config.yaml --log-level INFO --exp-from 5 -i 14 -p 25

