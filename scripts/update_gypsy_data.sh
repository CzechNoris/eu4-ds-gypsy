#!/bin/bash

echo "Which python to use?"
select python in $(ls /opt/homebrew/bin/python* /usr/bin/python* /usr/local/bin/python* /Users/$(whoami)/opt/anaconda3/bin/python* 2>/dev/null); do
    break
done


$python scripts/process_ideas.py -i data/raw/gypsy/common/ideas -o data/processed/gypsy
$python scripts/process_policies.py -i data/raw/gypsy/common/policies -o data/processed/gypsy

