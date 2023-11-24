import os
import re
import yaml

import argparse
import logging


def setup_logging(log_level):
    numeric_level = getattr(logging, log_level.upper(), None)
    if not isinstance(numeric_level, int):
        raise ValueError('Invalid log level: %s' % log_level)

    logging.basicConfig(level=numeric_level,
                        format='%(asctime)s %(levelname)s %(message)s')


parser = argparse.ArgumentParser(description='Generate build number')
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
        lines = f.readlines()

    # Line cleaning
    # Remove tags '# <<WIKI>>'
    # lines = [line.replace('# <<WIKI>>', '') for line in lines]
    # Remove comments
    lines = [line.split('#')[0] for line in lines]
    # Trim whitespace
    lines = [line.strip() for line in lines]
    # Remove empty lines
    lines = [line for line in lines if line]

    # Line extra formatting
    elements = []
    for line in lines:
        line = line.strip()
        while line:
            if '{' in line:
                opening_brace_index = line.index('{')
                if opening_brace_index > 0:
                    elements.append(line[:opening_brace_index].strip())
                elements.append('{')
                line = line[opening_brace_index + 1:]
            elif '}' in line:
                closing_brace_index = line.index('}')
                if closing_brace_index > 0:
                    elements.append(line[:closing_brace_index].strip())
                elements.append('}')
                line = line[closing_brace_index + 1:]
            else:
                elements.append(line)
                break

    # Process elements

    idea_blocks = {}
    current_idea = None
    bracket_counter = 0
    has_opening_bracket = False

    block_start_regex = re.compile(r'^\S+(\s.*|)=')
    category_regex = re.compile(r'^category(\s|=)')
    free_regex = re.compile(r'^free(\s|=)')

    for element in elements:
        if not current_idea and block_start_regex.match(element):
            current_idea = element.split('=')[0].strip()
            idea_blocks[current_idea] = []
        else:
            idea_blocks[current_idea].append(element)
            if element == '{':
                bracket_counter += 1
                has_opening_bracket = True
            elif element == '}':
                bracket_counter -= 1
            if bracket_counter == 0:
                if has_opening_bracket:
                    current_idea = None
                    has_opening_bracket = False

    idea_types = {}
    idea_sub_blocks = {}
    block_name = None
    bracket_counter = 0
    has_opening_bracket = False

    for idea_name, idea_block in idea_blocks.items():
        idea_sub_blocks[idea_name] = {}
        idea_types[idea_name] = 'country'
        for element in idea_block[1:-1]:
            try:
                if category_regex.match(element) and not has_opening_bracket:
                    idea_types[idea_name] = element.split('=')[1].strip()
                elif free_regex.match(element) and not has_opening_bracket:
                    pass
                elif not block_name and block_start_regex.match(element):
                    block_name = element.split('=')[0].strip()
                    idea_sub_blocks[idea_name][block_name] = []
                else:
                    idea_sub_blocks[idea_name][block_name].append(element)
                    if element == '{':
                        bracket_counter += 1
                        has_opening_bracket = True
                    elif element == '}':
                        bracket_counter -= 1
                    if bracket_counter == 0:
                        if has_opening_bracket:
                            block_name = None
                            has_opening_bracket = False
            except Exception as e:
                logging.error(
                    f'Could not process {idea_name} element: {element} -> {e}')

    idea_value_regex = re.compile(r'^\S+\s.*=\s.*\S+')

    ideas = {}
    skip_blocks = ['ai_will_do', 'trigger']
    for idea_name, idea_type in idea_types.items():
        ideas[idea_name] = {}
        ideas[idea_name]['type'] = idea_type
        ideas[idea_name]['effects'] = []
        for sub_name, sub_block in idea_sub_blocks[idea_name].items():
            if sub_name in skip_blocks:
                continue
            else:
                effects = {}
                for value in sub_block[1:-1]:
                    if idea_value_regex.match(value):
                        try:
                            value_name = value.split('=')[0].strip()
                            value_value = value.split('=')[1].strip()
                            if value_value == 'yes':
                                value_value = 1
                            elif value_name == 'no':
                                value_value = 0
                            else:
                                value_value = float(value_value)
                            effects[value_name] = value_value
                        except Exception as e:
                            logging.error(
                                f'Could not parse {idea_name}/{sub_name} value: {value}-> {e}')
                    else:
                        logging.debug(
                            f'Skipping {idea_name}/{sub_name} value: {value}')
                ideas[idea_name]['effects'].append(effects)

    # Quality check
    # Each idea has to have type
    for idea_name, idea in ideas.items():
        if 'type' not in idea:
            logging.warning(f'{idea_name}: Missing type')
    # Each idea should have 8 effects
    for idea_name, idea in ideas.items():
        if idea['type'] == 'country':
            if len(idea['effects']) != 9:
                logging.warning(f'{idea_name}: Missing effects')
        else:
            if len(idea['effects']) != 8:
                logging.warning(f'{idea_name}: Missing effects')
    # There should be no empty effect
    for idea_name, idea in ideas.items():
        for effect in idea['effects']:
            if not effect:
                logging.info(f'{idea_name}: Empty effect')

    # Save ideas
    output_path = os.path.join(args.output_folder_path, file_name + '.yaml')
    logging.info('Saving ideas to: %s', output_path)
    with open(output_path, 'w') as f:
        yaml.dump(ideas, f, default_flow_style=False)
