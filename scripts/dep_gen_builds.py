import os
import argparse
from collections import defaultdict, Counter
import random
from tqdm import tqdm

import sys
sys.path.append(os.path.join(os.path.dirname(os.path.abspath(__file__)), '..'))

from src.model import *
from build_tools import *
from src.loader_tools import *

from scripts.support_data import ADMIN_IDEAS, ADMIN_GOV_IDEAS, ADMIN_RELIGION_IDEAS, ADMIN_NOT_COMPATIBLE, DIPLO_IDEAS, DIPLO_NOT_COMPATIBLE, MIL_IDEAS, MIL_NOT_COMPATIBLE
 
parser = argparse.ArgumentParser(description='Generate build number')
parser.add_argument('-i', '--ideas', type=int, default=1, help='Total number of ideas to use.')
parser.add_argument('-w', '--weight', type=str, required=True, help='Path to the file with weights.')
parser.add_argument('-o', '--output', type=str, default='output', help='Path to output folder.')
parser.add_argument('-r', '--religion', type=str, default='katholisch0', help='Name of religion idea set.')  
parser.add_argument('-g', '--gov', type=str, default='monarchie0', help='Name of government idea set.')  
# parser.add_argument('-e', '--empire', type=bool, default=False, action="store_true", help='Name of government idea set.')  
args = parser.parse_args()

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

if args.religion not in ADMIN_RELIGION_IDEAS:
    print('Religion idea set not found!')
    exit()

if args.gov not in ADMIN_GOV_IDEAS:
    print('Government idea set not found!')
    exit()

IDEAS = load_ideas([
    'data/gypsy_transformed/ideas.yaml', 
    'data/gypsy_transformed/ideas_flogi.yaml', 
    'data/gypsy_transformed/ideas_flogi_relig.yaml'
])

POLICIES = load_policies([
    'data/gypsy_transformed/policies.yaml'
])

ADMIN_IDEA_SET = set(ADMIN_IDEAS + [args.religion, args.gov])
DIPLO_IDEA_SET = set(DIPLO_IDEAS) # + ['konigreich0' if args.empire else 'imperialismus']
MIL_IDEA_SET = set(MIL_IDEAS)

def compute_build(ideas: tuple[str], base_policy_slots=4, debug=False) -> Build:
    ideas_effect = get_ideas_effect(ideas, IDEAS)

    available_policies = get_available_policies(ideas, POLICIES)
    max_policy_slots = get_max_policy_slots(ideas_effect, base_policy_slots)

    micro_management_policies_effect = get_micro_management_policies_effect(ideas, available_policies, max_policy_slots)
    war_policies_effect = get_war_policies_effect(ideas, MILITARY_WEIGHTS, available_policies, max_policy_slots)

    total_effect = Counter()
    total_effect.update(ideas_effect)
    total_effect.update(micro_management_policies_effect)
    total_effect.update(war_policies_effect)

    return Build(
        ideas=ideas, 
        score=score(total_effect, [COUNTRY_WEIGHTS, MILITARY_WEIGHTS], debug=debug),
        total_effect=total_effect,
        war_policies_effect=war_policies_effect,
    )


IDEA_COUNT_THRESHOLD = 0.39

def expand_ideas(ideas: tuple):
    ideas_count = len(ideas)
    idea_set = set(ideas)
    adm_idea_count = len([x for x in ideas if x in ADMIN_IDEA_SET])
    dip_idea_count = len([x for x in ideas if x in DIPLO_IDEA_SET])
    mil_idea_count = len([x for x in ideas if x in MIL_IDEA_SET])
    if adm_idea_count / ideas_count < IDEA_COUNT_THRESHOLD:
        for idea in ADMIN_IDEA_SET:
            if idea not in idea_set:
                expanded_idea_set = idea_set.union({idea})
                for rule_A, rule_B in ADMIN_NOT_COMPATIBLE:
                    if rule_A in expanded_idea_set and rule_B in expanded_idea_set:
                        break
                else:
                    yield expanded_idea_set
    if dip_idea_count / ideas_count < IDEA_COUNT_THRESHOLD:
        for idea in DIPLO_IDEA_SET:
            if idea not in idea_set:
                expanded_idea_set = idea_set.union({idea})
                for rule_A, rule_B in DIPLO_NOT_COMPATIBLE:
                    if rule_A in expanded_idea_set and rule_B in expanded_idea_set:
                        break
                else:
                    yield expanded_idea_set
    if mil_idea_count / ideas_count < IDEA_COUNT_THRESHOLD:
        for idea in MIL_IDEA_SET:
            if idea not in idea_set:
                expanded_idea_set = idea_set.union({idea})
                for rule_A, rule_B in MIL_NOT_COMPATIBLE:
                    if rule_A in expanded_idea_set and rule_B in expanded_idea_set:
                        break
                else:
                    yield expanded_idea_set

def dump_builds(builds: list[Build], output_path: str, count: int = 100, highlights: list[str] = None):
    if highlights is None:
        highlights_mil = sorted(MILITARY_WEIGHTS.keys(), key=lambda x: MILITARY_WEIGHTS[x], reverse=True)
        highlights_country = sorted(COUNTRY_WEIGHTS.keys(), key=lambda x: COUNTRY_WEIGHTS[x], reverse=True)
        highlights = highlights_mil + highlights_country
    builds.sort(key=lambda x: x.score, reverse=True)
    with open(output_path, 'w') as f:
        for build in builds[:count]:
            f.write('---------------------------------------------------\n')
            f.write(f'Score: {build.score}\n')
            f.write(f'Ideas: {build.ideas}\n')
            f.write('     Main effects:\n')
            for highlight in highlights:
                f.write(f'          {highlight}: {build.total_effect.get(highlight, 0)}\n')
            f.write('     Other effects:\n')
            for effect, value in build.total_effect.items():
                if not effect in highlights:
                    f.write(f'          {effect}: {value}\n')
            f.write('     From war policies:\n')
            for effect, value in build.war_policies_effect.items():
                f.write(f'         {effect}: {value}\n')



builds = defaultdict(dict)

# Init 3-idea builds
total_options = len(ADMIN_IDEAS) *  len(DIPLO_IDEAS) * len(MIL_IDEAS)
with tqdm(total=total_options, desc='Creating tier 3') as pbar:
    for admin_idea in ADMIN_IDEAS:
        for diplo_idea in DIPLO_IDEAS:
            for mil_idea in MIL_IDEAS:
                idea_list = [admin_idea,  diplo_idea,  mil_idea]
                idea_list.sort()
                ideas = tuple(idea_list)
                build = compute_build(ideas)
                builds[3][ideas] = (build)
                pbar.update(1)

dump_builds(list(builds[3].values()), os.path.join(OUTPUT_FOLDER_PATH, 'builds_3.txt'))


# Expand builds
EXPAND_FROM_I = 6
EXPAND_BEST_N = 4000
EXPAND_RANDOM_N = 10000

def get_ideas_to_expand(build_list: list[Build], best_n=EXPAND_BEST_N, random_n=EXPAND_RANDOM_N):
    build_list.sort(key=lambda x: x.score, reverse=True)
    best_builds = build_list[:best_n]
    random_builds = random.sample(build_list[best_n:], random_n)
    return best_builds + random_builds


for i in range(4, args.ideas + 1):
    if i < EXPAND_FROM_I:
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
    dump_builds(list(builds[i].values()), os.path.join(OUTPUT_FOLDER_PATH, f'builds_{i}.txt'))
