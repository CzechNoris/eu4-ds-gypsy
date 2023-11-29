#!/usr/bin/env python

import os
import yaml
import ClauseWizard

import argparse
import logging


def setup_logging(log_level):
    numeric_level = getattr(logging, log_level.upper(), None)
    if not isinstance(numeric_level, int):
        raise ValueError('Invalid log level: %s' % log_level)
    logging.basicConfig(level=numeric_level,
                        format='%(asctime)s %(levelname)s %(message)s')


parser = argparse.ArgumentParser(
    description='Process EU4 idea files into YAML format.')
parser.add_argument('--log-level', dest='log_level', default='WARN',
                    choices=['DEBUG', 'INFO', 'WARN', 'ERROR', 'CRITICAL'],
                    help='Set the logging level (default: warning)')
parser.add_argument('-i', '--input_path', type=str,
                    required=True, help='Path to the file to process.')
parser.add_argument('-o', '--output_folder_path', type=str,
                    required=True, help='Path to output folder.')
args = parser.parse_args()
setup_logging(args.log_level)

if 'data/processed/' not in args.output_folder_path:
    logging.warning('Output folder should be under data/processed/!')

if not os.path.exists(args.output_folder_path):
    logging.info('Creating output folder: %s', args.output_folder_path)
    os.makedirs(args.output_folder_path)

if os.path.isdir(args.input_path):
    file_paths = [os.path.join(args.input_path, file_name)
                  for file_name in os.listdir(args.input_path)]
else:
    file_paths = [args.input_path]

for file_path in file_paths:
    logging.info('Processing file: %s', file_path)
    file_name = os.path.basename(file_path)
    file_name = os.path.splitext(file_name)[0]

    with open(file_path, 'r') as f:
        tokens = ClauseWizard.cwparse(f.read())
        obj = ClauseWizard.cwformat(tokens)

    # Replace defaultdicts with dicts
    def dictify(d):
        if isinstance(d, dict):
            return {k: dictify(v) for k, v in d.items()}
        elif isinstance(d, list):
            return [dictify(x) for x in d]
        elif isinstance(d, set):
            return {dictify(x) for x in d}
        else:
            return d
    obj = dictify(obj)
    
    # Remove ideas with Trigger-always = no

    ideas_to_remove = []
    for k, v in obj.items():
        if 'trigger' in v:
            if 'always' in v['trigger']:
                if v['trigger']['always'] == False:
                    ideas_to_remove.append(k)
    logging.info('Ignored ideas (trigger always no):', ideas_to_remove)
    for k in ideas_to_remove:
        del obj[k]

    # Remove keys: ai_will_do, trigger, important, free

    for k, v in obj.items():
        if 'ai_will_do' in v:
            del v['ai_will_do']
        if 'trigger' in v:
            del v['trigger']
        if 'important' in v:
            del v['important']
        if 'free' in v:
            del v['free']

    # Quality check
    # - every object has exactly 9 keys
    # - every object has to have keys: category or start, bonus
    # - category value is a str: ADM, DIP, MIL
    # - eight key values are of type dict

    IDEA_CATEGORY_VALUES = ['ADM', 'DIP', 'MIL']
    for k, v in obj.items():
        if len(v) != 9:
            logging.warning(f'Object {k} has {len(v)} keys')
        if 'category' not in v:
            if 'start' not in v:
                logging.error(f'Object {k} has no category or start key')
        else:
            v['category'] = v['category'].upper()
            if v['category'] not in IDEA_CATEGORY_VALUES:
                logging.error(f'Object {k} has category {v["category"]}')
        idea_keys = [k for k in v.keys() if k != 'category']
        for key in idea_keys:
            if not isinstance(v[key], dict):
                logging.warning(f'Object {k} has no dict value for key {key}')
                del v[key]

    # Save ideas
    output_path = os.path.join(args.output_folder_path, file_name + '.yaml')
    with open(output_path, 'w') as f:
        yaml.dump(obj, f, default_flow_style=False)
