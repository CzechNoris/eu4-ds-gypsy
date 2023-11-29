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
    description='Process EU4 policy files into YAML format.')
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

   # Remove keys: ai_will_do, potential
    for k, v in obj.items():
        if 'ai_will_do' in v:
            del v['ai_will_do']
        if 'potential' in v:
            del v['potential']

    # Quality check
    # - every object has to have keys: monarch_power, allow
    # - monarch_power value is a str: ADM, DIP, MIL
    # - there are at least 3 keys in the object
    POLICY_SLOT_VALUES = ['ADM', 'DIP', 'MIL']
    for k, v in obj.items():
        if 'monarch_power' not in v:
            logging.error(f'{k}: no monarch_power')
        else: 
            v['monarch_power'] = v['monarch_power'].upper()
            if v['monarch_power'] not in POLICY_SLOT_VALUES:
                logging.error(f'{k}: wrong monarch_power value: {v["monarch_power"]}')
        if 'allow' not in v:
            logging.error(f'{k}: missing allow')
        if len(v.keys()) < 3:
            logging.warning(f'{k}: too few keys')    
                      
    # Parse allow section
    rel_idea_names = ['religious_ideas', 'anglican0', 'animist0', 'buddhism0', 'cathar0', 'catholic0', 'confucian0', 'coptic0', 'dreamtime0', 'fetishist0', 'hellenic0', 'hindu0', 'hussite0', 'ibadi0', 'inti0', 'jewish0', 'manichean0', 'mesoamerican0', 'nahuatl0', 'norse0', 'orthodox0', 'protestant0', 'reformed0', 'romuva0', 'shia0', 'shinto0', 'slavic0', 'sunni0', 'suomi0', 'tengri0', 'totemist0', 'zoroastrian0']
    gov_idea_names = ['dictatorship0', 'horde0', 'monarchy0', 'republic0', 'theocracy0']
    for k, v in obj.items():
        allow_keys = v['allow'].keys()
        if len(allow_keys) == 1:
            if 'full_idea_group' in allow_keys:
                full_idea_group = v['allow']['full_idea_group']
                if isinstance(full_idea_group, list) and len(full_idea_group) == 2:
                    v['req'] = ([full_idea_group[0]], [full_idea_group[1]])
                else:
                    logging.warning(f'{k}: unknown allow structure: {v["allow"]}')
            elif 'OR' in allow_keys:
                OR_group = v['allow']['OR']
                if isinstance(OR_group, list) and len(OR_group) == 2 and 'full_idea_group' in OR_group[0] and 'full_idea_group' in OR_group[1]:
                    v['req'] = (OR_group[0]['full_idea_group'], OR_group[1]['full_idea_group'])
                else:
                    logging.warning(f'{k}: unknown allow structure: {v["allow"]}')
            else:
                logging.warning(f'{k}: unknown allow structure: {v["allow"]}')
        elif len(allow_keys) == 2:
            full_idea_group, government_ideas_group, religious_ideas_group, OR_group = None, None, None, None
            if 'full_idea_group' in allow_keys and isinstance(v['allow']['full_idea_group'], str):
                full_idea_group = v['allow']['full_idea_group']
            if 'has_completed_government_ideas_group' in allow_keys and isinstance(v['allow']['has_completed_government_ideas_group'], bool):
                government_ideas_group = v['allow']['has_completed_government_ideas_group']
            if 'has_completed_religious_ideas_group' in allow_keys and isinstance(v['allow']['has_completed_religious_ideas_group'], bool):
                religious_ideas_group = v['allow']['has_completed_religious_ideas_group']
            if 'OR' in allow_keys and isinstance(v['allow']['OR'], dict) and 'full_idea_group' in v['allow']['OR']:
                OR_group = v['allow']['OR']
        # Exactly 2 requirements has to be not None
            if sum([full_idea_group is not None, government_ideas_group is not None, religious_ideas_group is not None, OR_group is not None]) != 2:
                logging.warning(f'{k}: unknown allow structure: {v["allow"]}')
            else:
                if full_idea_group is not None and government_ideas_group:
                    v['req'] = [full_idea_group], gov_idea_names
                elif full_idea_group is not None and religious_ideas_group:
                    v['req'] = [full_idea_group], rel_idea_names
                elif full_idea_group is not None and OR_group is not None:
                    v['req'] = [full_idea_group], OR_group['full_idea_group']
                elif government_ideas_group and religious_ideas_group:
                    v['req'] = gov_idea_names, rel_idea_names
                elif government_ideas_group and OR_group is not None:
                    v['req'] = gov_idea_names, OR_group['full_idea_group']
                elif religious_ideas_group and OR_group is not None:
                    v['req'] = rel_idea_names, OR_group['full_idea_group']
                else:
                    logging.warning(f'{k}: unknown allow structure: {v["allow"]}')
        else:
            logging.warning(f'{k}: unknown allow structure: {v["allow"]}')
            
    # Second quality check
    # - remove allow key from every object
    # - every object has to have keys req which is a tuple of 2 lists
    for k, v in obj.items():
        if 'allow' in v:
            del v['allow']
        if 'req' not in v:
            logging.error(f'{k}: no req after parsing allow')
        else:
            if not isinstance(v['req'], tuple):
                logging.warning(f'{k}: req is not a tuple')
            else:
                if len(v['req']) != 2:
                    logging.warning(f'{k}: req tuple has wrong length: {len(v["req"])}')
                else:
                    if not isinstance(v['req'][0], list):
                        logging.warn(f'Wrong req[0] type in {k}: {v["req"]}')
                    if not isinstance(v['req'][1], list):
                        logging.warn(f'Wrong req[1] type in {k}: {v["req"]}')

    # Save ideas
    output_path = os.path.join(args.output_folder_path, file_name + '.yaml')
    with open(output_path, 'w') as f:
        yaml.dump(obj, f, default_flow_style=False)
