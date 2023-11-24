import os
import yaml
import random
import numpy as np

from collections import defaultdict, Counter

import argparse
import logging
from tqdm import tqdm

try:
    import sys
    sys.path.append(os.path.join(
        os.path.dirname(os.path.abspath(__file__)), '..'))
    from src.loader_tools import *
    from src.build_tools import *
    from src.model import *
except:
    raise Exception('Run this script from the root folder of the project!')


def setup_logging(log_level):
    numeric_level = getattr(logging, log_level.upper(), None)
    if not isinstance(numeric_level, int):
        raise ValueError('Invalid log level: %s' % log_level)
    logging.basicConfig(
        level=numeric_level,
        format='%(levelname)s %(message)s',
        # format='%(asctime)s %(levelname)s %(message)s',
    )

########################################################################
### Parse arguments ####################################################
########################################################################


parser = argparse.ArgumentParser(description='Generate GYPSY builds.')
parser.add_argument('--log-level', dest='log_level', default='INFO',
                    choices=['DEBUG', 'INFO', 'WARN', 'ERROR', 'CRITICAL'],
                    help='Set the logging level (default: warning)')
parser.add_argument('-i', '--ideas', type=int, default=10,
                    help='Total number of ideas to use.')
parser.add_argument('-w', '--weight', type=str, required=True,
                    help='Path to the file with weights.')
parser.add_argument('-o', '--output', type=str,
                    default='output', help='Path to output folder.')
parser.add_argument('-r', '--religion', type=str, default='catholic0',
                    help='Name of religion idea set.')
parser.add_argument('-g', '--gov', type=str, default='monarchy0',
                    help='Name of government idea set.')
parser.add_argument('-e', '--empire',
                    action="store_true", help='Use imperialism0 instead of imperial_ambition0.')
parser.add_argument('-p', '--potential-filtering', type=int, 
                    help='Filter out ideas with the lowest potential. Insert percentage (0-100).')
parser.add_argument('-s', '--start-i-count', type=int, default=3,
                    choices=[3, 6], help='Number of ideas to start with.')
parser.add_argument('--exp-from', type=int,
                    default=5, help='Combinatorics counts grow rapidly, therefore from some idea count, we need to expand only on exp_top and exp_rand builds.')
parser.add_argument('--exp-top', type=int,
                    default=4000, help='When expanding, take top exp_top builds.')
parser.add_argument('--exp-rand', type=int,
                    default=10000, help='When expanding, take exp_rand random builds.')
parser.add_argument('-f', '--force', action='store_true',
                    help='Do not use potential filtering.')
args = parser.parse_args()
setup_logging(args.log_level)


########################################################################
### Check arguments ####################################################
########################################################################

if args.ideas < 3 or args.ideas > 15:
    print('Number of ideas has to be in range [3, 15]!')
    exit()

weight_file_name = os.path.basename(args.weight)
weight_file_name = os.path.splitext(weight_file_name)[0]

OUTPUT_FOLDER_PATH = os.path.join(args.output, weight_file_name)
if not os.path.exists(OUTPUT_FOLDER_PATH):
    os.makedirs(OUTPUT_FOLDER_PATH)

with open(args.weight, 'r') as f:
    weights = yaml.safe_load(f)
COUNTRY_WEIGHTS = weights['country']
MILITARY_WEIGHTS = weights['military']
EXTRA_WEIGHTS = weights['extra']


########################################################################
### Load data ##########################################################
########################################################################

IDEAS = load_ideas([
    'data/processed/gypsy-1-36-1/00_basic_ideas.yaml',
    'data/processed/gypsy-1-36-1/00_flogi_ideas.yaml',
])

POLICIES = load_policies([
    'data/processed/gypsy-1-36-1/Idea_Variation_policies.yaml'
])

########################################################################
### Set consts #########################################################
########################################################################

ADM_IDEA_NAMES = ['administrative_ideas', 'economic_ideas', 'expansion_ideas', 'humanist_ideas', 'innovativeness_ideas',
                  'centralisation0', 'decentralisation0', 'development0', 'jurisprudence0', 'state_administration0', 'strongman0',]
REL_IDEA_NAMES = [args.religion,]
GOV_IDEA_NAMES = [args.gov,]
ADM_NOT_COMPATIBLE = [
    ('strongfem0', 'strongman0',),
    ('centralisation0', 'decentralisation0',),
]
ADM_IDEA_SCOPE = ADM_IDEA_NAMES + REL_IDEA_NAMES + GOV_IDEA_NAMES

DIP_IDEA_NAMES = ['dynasty0', 'exploration_ideas', 'influence_ideas', 'maritime_ideas', 'spy_ideas', 'trade_ideas', 'assimilation0',
                  'colonial_empire0', 'fleet_base0', 'galley0', 'heavy_ship0', 'light_ship0', 'nationalism0', 'propaganda0', 'society0']
IMP_IDEA_NAMES = ['imperial_ambition0' if not args.empire else 'imperialism0',]
DIP_NOT_COMPATIBLE = [
    ('galley0', 'heavy_ship0'),
    ('galley0', 'light_ship0'),
    ('heavy_ship0', 'light_ship0'),
]
DIP_IDEA_SCOPE = DIP_IDEA_NAMES + IMP_IDEA_NAMES

MIL_IDEA_NAMES = ['offensive0', 'defensive0', 'quality0', 'quantity0', 'general_staff0', 'standing_army0', 'conscription0',
                  'mercenary0', 'weapon_quality0', 'fortress0', 'war_production0', 'tactical0', 'militarism0', 'fire0', 'shock0',]
MIL_NOT_COMPATIBLE = [
    ('offensive0', 'defensive0'),
    ('quality0', 'quantity0'),
    ('standing_army0', 'conscription0'),
    ('fire0', 'shock0')
]
MIL_IDEA_SCOPE = MIL_IDEA_NAMES

ALL_IDEA_NAMES = ADM_IDEA_SCOPE + DIP_IDEA_SCOPE + MIL_IDEA_SCOPE

# Check if all idea names are valid
for idea_name in ALL_IDEA_NAMES:
    if idea_name not in IDEAS:
        logging.critical(f'Idea {idea_name} not found!')
        exit()

########################################################################
### Potential filtering ################################################
########################################################################

if args.force:
    logging.info('Consider not forcing and using potential filtering!')
else:
    idea_potential_score = {}
    for idea_name in ALL_IDEA_NAMES:
        idea = IDEAS[idea_name]
        idea_potential_score[idea_name] = score(
            idea.effect, [COUNTRY_WEIGHTS, MILITARY_WEIGHTS]) + EXTRA_WEIGHTS.get(idea_name, 0)
    idea_policies_potential_score = Counter()
    for idea_name in ALL_IDEA_NAMES:
        available_policies = [
            policy for policy in POLICIES if idea_name in policy.req[0] or idea_name in policy.req[1]]
        for policy in available_policies:
            idea_policies_potential_score[idea_name] += score(
                policy.effect, [COUNTRY_WEIGHTS, MILITARY_WEIGHTS])
    combined_potential_score = {}
    for idea_name in ALL_IDEA_NAMES:
        combined_potential_score[idea_name] = idea_potential_score[idea_name] + \
            idea_policies_potential_score[idea_name]

    combined_potential_scores = np.array(
        list(combined_potential_score.values()))
    logging.info('Based on the input weights. Stats of the potential idea scores: \n'
                 f' mean: {combined_potential_scores.mean():.2f}, \n'
                 f' std: {combined_potential_scores.std():.2f}, \n'
                 f' min: {combined_potential_scores.min():.2f}, \n'
                 f' max: {combined_potential_scores.max():.2f}, \n'
                 f' median: {np.median(combined_potential_scores):.2f}, \n'
                 f' 75% percentile: {np.quantile(combined_potential_scores, 0.75):.2f}, \n'
                 f' 90% percentile: {np.quantile(combined_potential_scores, 0.9):.2f}')

    logging.debug(f'Idea potential scores: {combined_potential_score}')
    
    if args.potential_filtering is None:
        potential_filtering = input(
            'Enter potential threshold in percent (0-100): [25]')
        if potential_filtering == '':
            potential_filtering = 25
        else:
            potential_filtering = int(potential_filtering)
    else:
        potential_filtering = args.potential_filtering
    logging.info(
            f'Potential filtering: {potential_filtering}% of least potential ideas will be filtered out.')
    
    # Filter out ideas with the lowest potential
    potential_threshold = np.quantile(
        combined_potential_scores, potential_filtering / 100)
    ADM_IDEA_SCOPE = [
        idea_name for idea_name in ADM_IDEA_SCOPE if combined_potential_score[idea_name] >= potential_threshold]
    DIP_IDEA_SCOPE = [
        idea_name for idea_name in DIP_IDEA_SCOPE if combined_potential_score[idea_name] >= potential_threshold]
    MIL_IDEA_SCOPE = [
        idea_name for idea_name in MIL_IDEA_SCOPE if combined_potential_score[idea_name] >= potential_threshold]
    ideas_to_be_filtered_out = [ 
        idea_name for idea_name in ALL_IDEA_NAMES if combined_potential_score[idea_name] < potential_threshold]
    logging.debug(f'Ideas to be filtered out: {ideas_to_be_filtered_out}')

########################################################################
### Not shared sup #####################################################
########################################################################


def compute_build(ideas: tuple[str], base_policy_slots=4, debug=False) -> Build:
    ideas_effect = get_ideas_effect(ideas, IDEAS)

    available_policies = get_available_policies(ideas, POLICIES)
    max_policy_slots = get_max_policy_slots(ideas_effect, base_policy_slots)

    micro_management_policies_effect = get_micro_management_policies_effect(
        ideas, available_policies, max_policy_slots)
    war_policies_effect = get_war_policies_effect(
        ideas, MILITARY_WEIGHTS, available_policies, max_policy_slots)

    total_effect = Counter()
    total_effect.update(ideas_effect)
    total_effect.update(micro_management_policies_effect)
    total_effect.update(war_policies_effect)

    return Build(
        ideas=ideas,
        score=score(total_effect, [COUNTRY_WEIGHTS,
                    MILITARY_WEIGHTS], debug=debug),
        total_effect=total_effect,
        war_policies_effect=war_policies_effect,
    )


def expand_ideas(ideas: tuple, idea_count_threshold=0.39):
    ideas_count = len(ideas)
    idea_set = set(ideas)
    adm_idea_count = len([x for x in ideas if x in ADM_IDEA_SCOPE])
    dip_idea_count = len([x for x in ideas if x in DIP_IDEA_SCOPE])
    mil_idea_count = len([x for x in ideas if x in MIL_IDEA_SCOPE])
    if adm_idea_count / ideas_count < idea_count_threshold:
        for idea in ADM_IDEA_SCOPE:
            if idea not in idea_set:
                expanded_idea_set = idea_set.union({idea})
                for rule_A, rule_B in ADM_NOT_COMPATIBLE:
                    if rule_A in expanded_idea_set and rule_B in expanded_idea_set:
                        break
                else:
                    yield expanded_idea_set
    if dip_idea_count / ideas_count < idea_count_threshold:
        for idea in DIP_IDEA_SCOPE:
            if idea not in idea_set:
                expanded_idea_set = idea_set.union({idea})
                for rule_A, rule_B in DIP_NOT_COMPATIBLE:
                    if rule_A in expanded_idea_set and rule_B in expanded_idea_set:
                        break
                else:
                    yield expanded_idea_set
    if mil_idea_count / ideas_count < idea_count_threshold:
        for idea in MIL_IDEA_SCOPE:
            if idea not in idea_set:
                expanded_idea_set = idea_set.union({idea})
                for rule_A, rule_B in MIL_NOT_COMPATIBLE:
                    if rule_A in expanded_idea_set and rule_B in expanded_idea_set:
                        break
                else:
                    yield expanded_idea_set


def dump_builds(builds: list[Build], output_path: str, count: int = 100, highlights: list[str] = None):
    if highlights is None:
        highlights_mil = sorted(MILITARY_WEIGHTS.keys(
        ), key=lambda x: MILITARY_WEIGHTS[x], reverse=True)
        highlights_country = sorted(COUNTRY_WEIGHTS.keys(
        ), key=lambda x: COUNTRY_WEIGHTS[x], reverse=True)
        highlights = highlights_mil + highlights_country
    builds.sort(key=lambda x: x.score, reverse=True)
    with open(output_path, 'w') as f:
        for build in builds[:count]:
            f.write('---------------------------------------------------\n')
            f.write(f'Score: {build.score}\n')
            f.write(f'Ideas: {build.ideas}\n')
            f.write('     Main effects:\n')
            for highlight in highlights:
                f.write(
                    f'          {highlight}: {build.total_effect.get(highlight, 0)}\n')
            f.write('     Other effects:\n')
            for effect, value in build.total_effect.items():
                if not effect in highlights:
                    f.write(f'          {effect}: {value}\n')
            f.write('     From war policies:\n')
            for effect, value in build.war_policies_effect.items():
                f.write(f'         {effect}: {value}\n')

########################################################################
### Main init builds ###################################################
########################################################################

builds = defaultdict(dict)

# Init builds
if args.start_i_count == 3:
    total_options = len(ADM_IDEA_SCOPE) * \
        len(DIP_IDEA_SCOPE) * len(MIL_IDEA_SCOPE)
    with tqdm(total=total_options, desc='Creating tier 3') as pbar:
        for adm_idea in ADM_IDEA_SCOPE:
            for dip_idea in DIP_IDEA_SCOPE:
                for mil_idea in MIL_IDEA_SCOPE:
                    ideas = tuple(sorted([adm_idea,  dip_idea,  mil_idea]))
                    build = compute_build(ideas)
                    builds[3][ideas] = (build)
                    pbar.update(1)
    dump_builds(list(builds[3].values()), os.path.join(
        OUTPUT_FOLDER_PATH, 'builds_3.txt'))
elif args.start == 6:
    total_options = len(ADM_IDEA_SCOPE) * len(DIP_IDEA_SCOPE) * len(MIL_IDEA_SCOPE) * \
        (len(ADM_IDEA_SCOPE) - 1) * \
        (len(DIP_IDEA_SCOPE) - 1) * (len(MIL_IDEA_SCOPE) - 1)
    with tqdm(total=total_options, desc='Creating tier 6') as pbar:
        for adm_idea_0 in ADM_IDEA_SCOPE:
            for dip_idea_0 in DIP_IDEA_SCOPE:
                for mil_idea_0 in MIL_IDEA_SCOPE:
                    for adm_idea_1 in ADM_IDEA_SCOPE:
                        for dip_idea_1 in DIP_IDEA_SCOPE:
                            for mil_idea_1 in MIL_IDEA_SCOPE:
                                ideas = tuple(sorted(
                                    [adm_idea_0, dip_idea_0, mil_idea_0, adm_idea_1, dip_idea_1, mil_idea_1]))
                                build = compute_build(ideas)
                                builds[6][ideas] = (build)
                                pbar.update(1)
    dump_builds(list(builds[3].values()), os.path.join(
        OUTPUT_FOLDER_PATH, 'builds_6.txt'))

########################################################################
### Main expand builds #################################################
########################################################################

def get_ideas_to_expand(build_list: list[Build], best_n=args.exp_top, random_n=args.exp_rand):
    build_list.sort(key=lambda x: x.score, reverse=True)
    best_builds = build_list[:best_n]
    random_builds = random.sample(build_list[best_n:], min(random_n, len(build_list[best_n:])))
    return best_builds + random_builds


for i in range(args.start_i_count + 1, args.ideas + 1):
    if i < args.exp_from:
        for ideas in tqdm(builds[i - 1].keys(), desc=f'Creating tier {i}'):
            for new_idea_set in expand_ideas(ideas):
                idea_list = list(new_idea_set)
                idea_list.sort()
                new_ideas = tuple(idea_list)
                new_build = compute_build(new_ideas)
                builds[i][new_ideas] = new_build
    else:
        builds_to_expand = get_ideas_to_expand(list(builds[i - 1].values()))
        for build in tqdm(builds_to_expand, desc=f'Creating tier {i}'):
            for new_idea_set in expand_ideas(build.ideas):
                idea_list = list(new_idea_set)
                idea_list.sort()
                new_ideas = tuple(idea_list)
                new_build = compute_build(new_ideas)
                builds[i][new_ideas] = new_build
    dump_builds(list(builds[i].values()), os.path.join(
        OUTPUT_FOLDER_PATH, f'builds_{i}.txt'))
