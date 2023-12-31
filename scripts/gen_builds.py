#!/usr/bin/env python

import os
import yaml
import copy
import pickle
import random
import numpy as np
import bisect
from collections import defaultdict, Counter

import argparse
import datetime

import logging
from tqdm import tqdm


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
parser.add_argument('-b', '--build_config', type=str, required=True,
                    help='Path to the file with build config.')
parser.add_argument('-o', '--output', type=str,
                    default='generated/builds', help='Path to output folder.')
parser.add_argument('-r', '--religion', type=str,
                    help='Name of religion idea set.')
parser.add_argument('-g', '--gov', type=str, default='monarchy0',
                    help='Name of government idea set.')
parser.add_argument('-e', '--empire',
                    action="store_true", help='Use imperialism0 instead of imperial_ambition0.')
parser.add_argument('-s', '--base_policy_slots', type=int, default=4,
                    help='Number of base policy slots.')
parser.add_argument('-p', '--potential-filtering', type=int,
                    help='Filter out ideas with the lowest potential. Insert percentage (0-100).')
parser.add_argument('--exp-from', type=int,
                    default=4, help='Combinatorics counts grow rapidly, therefore from some idea count, we need to expand only on exp_top and exp_rand builds.')
parser.add_argument('--exp-top', type=int,
                    default=4000, help='When expanding, take top exp_top builds.')
parser.add_argument('--exp-rand', type=int,
                    default=10000, help='When expanding, take exp_rand random builds.')
parser.add_argument('-f', '--force', action='store_true',
                    help='Do not use potential filtering.')
args = parser.parse_args()
setup_logging(args.log_level)

########################################################################
### Stats ##############################################################
########################################################################

start_time = datetime.datetime.now()

########################################################################
### Check arguments ####################################################
########################################################################

if args.ideas < 3 or args.ideas > 15:
    logging.error('Number of ideas has to be in range [3, 15]!')
    exit()

########################################################################
### Load build config ##################################################
########################################################################

build_config_name = os.path.basename(args.build_config)
build_config_name = os.path.splitext(build_config_name)[0]

OUTPUT_FOLDER_PATH = os.path.join(args.output, build_config_name)
if not os.path.exists(OUTPUT_FOLDER_PATH):
    os.makedirs(OUTPUT_FOLDER_PATH)

with open(args.build_config, 'r') as f:
    build_config = yaml.safe_load(f)

HIGHLIGHTS = build_config['highlights']

build_weights = build_config['weights']
COUNTRY_WEIGHTS = build_weights['country']
MILITARY_WEIGHTS = build_weights['military']
IDEA_WEIGHTS = build_weights['ideas']

LIMITS = defaultdict(lambda: 100)
if 'limits' in build_config:
    for key, value in build_config['limits'].items():
        LIMITS[key] = value

########################################################################
### Defaults ###########################################################
########################################################################

build_defaults = build_config.get('defaults')

if not args.religion:
    if build_defaults and 'religion' in build_defaults:
        args.religion = build_defaults['religion']
    else:
        args.religion = 'catholic0'

if not args.gov:
    if build_defaults and 'government' in build_defaults:
        args.gov = build_defaults['government']
    else:
        args.gov = 'monarchy0'

if not args.empire:
    if build_defaults and 'empire' in build_defaults:
        args.empire = build_defaults['empire']
    else:
        args.empire = True

########################################################################
### Model ##############################################################
########################################################################


class Idea():
    def __init__(self, name: str, type: str, effect: dict):
        self.name = name
        self.type = type
        self.effect = effect

    def __repr__(self):
        return f'Idea({self.name}, {self.type}, {self.effect})'


class Policy():
    def __init__(self, name: str, type: str, req: tuple, effect: dict):
        self.name = name
        self.type = type.upper()
        self.req = req
        self.effect = effect
        assert self.type in ['ADM', 'DIP', 'MIL']

    def __repr__(self):
        return f"Policy({self.name}, {self.type}, {self.req}, {self.effect})"


class Build():
    POLICY_TYPE_INDEX = {'ADM': 0, 'DIP': 1, 'MIL': 2}

    def __init__(self,
                 idea_set: set[str] = None,
                 idea_counts: [int, int, int] = None,
                 cum_idea_score: float = 0,
                 ideas_effect: Counter = None,
                 policy_set: set[str] = None,
                 max_policies: tuple[int, int, int] = None,
                 war_policies: tuple[list[tuple[float, str]],
                                     list[tuple[float, str]], list[tuple[float, str]]] = None,
                 dev_policies: tuple[list[tuple[float, str]],
                                     list[tuple[float, str]], list[tuple[float, str]]] = None,
                 adm_tech_policies: tuple[list[tuple[float, str]],
                                          list[tuple[float, str]], list[tuple[float, str]]] = None,
                 dip_tech_policies: tuple[list[tuple[float, str]],
                                          list[tuple[float, str]], list[tuple[float, str]]] = None,
                 mil_tech_policies: tuple[list[tuple[float, str]],
                                          list[tuple[float, str]], list[tuple[float, str]]] = None,
                 idea_policies: tuple[list[tuple[float, str]],
                                      list[tuple[float, str]], list[tuple[float, str]]] = None,
                 total_score: float = 0,
                 ):
        self.idea_set = idea_set if idea_set is not None else set()
        self.idea_counts = idea_counts if idea_counts is not None else (
            0, 0, 0)
        self.cum_idea_score = cum_idea_score if cum_idea_score is not None else 0
        self.ideas_effect = ideas_effect if ideas_effect is not None else Counter()
        self.policy_set = policy_set if policy_set is not None else set()
        self.max_policies = max_policies if max_policies is not None else (
            4, 4, 4)
        self.war_policies = war_policies if war_policies is not None else ([], [
        ], [])
        self.dev_policies = dev_policies if dev_policies is not None else ([], [
        ], [])
        self.adm_tech_policies = adm_tech_policies if adm_tech_policies is not None else ([
        ], [], [])
        self.dip_tech_policies = dip_tech_policies if dip_tech_policies is not None else ([
        ], [], [])
        self.mil_tech_policies = mil_tech_policies if mil_tech_policies is not None else ([
        ], [], [])
        self.idea_policies = idea_policies if idea_policies is not None else ([], [
        ], [])
        self.total_score = total_score if total_score is not None else 0

    def __repr__(self):
        return f"Build( {self.total_score:.2f} - ideas: {self.idea_set}"

    def print(self):
        print(f"Build( {self.total_score:.2f} - ideas: {self.idea_set}")
        print(f"    - Idea counts: {self.idea_counts}")
        print(f"    - Idea score: {self.cum_idea_score:.2f}")
        print(f"    - Idea effect: {self.ideas_effect}")
        print(f"    - Policies: {self.policy_set}")
        print(f"    - Max policies: {self.max_policies}")
        print(f"    - War policies: {self.war_policies}")
        print(f"    - Dev policies: {self.dev_policies}")
        print(f"    - Adm tech policies: {self.adm_tech_policies}")
        print(f"    - Dip tech policies: {self.dip_tech_policies}")
        print(f"    - Mil tech policies: {self.mil_tech_policies}")
        print(f"    - Idea policies: {self.idea_policies}")
        print(f"    - Total score: {self.total_score:.2f}")


########################################################################
### Load data ##########################################################
########################################################################

IDEA_PROTECTED_KEYS = ['category']


def load_ideas(file_paths: list[str]) -> dict[str, Idea]:
    ideas = {}
    for path in file_paths:
        with open(path, 'r') as f:
            ideas_dict = yaml.load(f, Loader=yaml.FullLoader)
        for name, value in ideas_dict.items():
            category = value['category']
            effect = Counter()
            for key in value.keys():
                if key not in IDEA_PROTECTED_KEYS:
                    effect_set = value[key]
                    for k, v in effect_set.items():
                        effect[k] += abs(v)
            ideas[name] = Idea(name=name, type=category, effect=effect)
    return ideas


POLICY_PROTECTED_KEYS = ['monarch_power', 'req']


def load_policies(file_paths: list[str]) -> list[Policy]:
    policies = {}
    for path in file_paths:
        with open(path, 'r') as f:
            policies_dict = yaml.load(f, Loader=yaml.FullLoader)
        for name, value in policies_dict.items():
            monarch_power = value['monarch_power']
            req0, req1 = value['req']
            effect = Counter()
            for key in value.keys():
                if key not in POLICY_PROTECTED_KEYS:
                    effect[key] = abs(value[key])
            policies[name] = Policy(
                name=name,
                type=monarch_power,
                req=(req0, req1),
                effect=effect
            )
    return policies


IDEAS = load_ideas([
    'data/processed/gypsy/00_basic_ideas.yaml',
    'data/processed/gypsy/00_flogi_ideas.yaml',
])

POLICIES = load_policies([
    'data/processed/gypsy/Idea_Variation_policies.yaml'
])

########################################################################
### Set CONSTs #########################################################
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
ADM_IDEA_SCOPE_SET = set(ADM_IDEA_SCOPE)
ADM_IDEA_SCOPE_COUNT = len(ADM_IDEA_SCOPE)

DIP_IDEA_NAMES = ['dynasty0', 'exploration_ideas', 'influence_ideas', 'maritime_ideas', 'spy_ideas', 'trade_ideas', 'assimilation0',
                  'colonial_empire0', 'fleet_base0', 'galley0', 'heavy_ship0', 'light_ship0', 'nationalism0', 'propaganda0', 'society0']
IMP_IDEA_NAMES = ['imperial_ambition0' if not args.empire else 'imperialism0',]
DIP_NOT_COMPATIBLE = [
    ('galley0', 'heavy_ship0'),
    ('galley0', 'light_ship0'),
    ('heavy_ship0', 'light_ship0'),
]
DIP_IDEA_SCOPE = DIP_IDEA_NAMES + IMP_IDEA_NAMES
DIP_IDEA_SCOPE_SET = set(DIP_IDEA_SCOPE)
DIP_IDEA_SCOPE_COUNT = len(DIP_IDEA_SCOPE)

MIL_IDEA_NAMES = ['offensive0', 'defensive0', 'quality0', 'quantity0', 'general_staff0', 'standing_army0', 'conscription0',
                  'mercenary0', 'weapon_quality0', 'fortress0', 'war_production0', 'tactical0', 'militarism0', 'fire0', 'shock0',]
MIL_NOT_COMPATIBLE = [
    ('offensive0', 'defensive0'),
    ('quality0', 'quantity0'),
    ('standing_army0', 'conscription0'),
    ('fire0', 'shock0')
]
MIL_IDEA_SCOPE = MIL_IDEA_NAMES
MIL_IDEA_SCOPE_SET = set(MIL_IDEA_SCOPE)
MIL_IDEA_SCOPE_COUNT = len(MIL_IDEA_SCOPE)

ALL_IDEA_NAMES = ADM_IDEA_SCOPE + DIP_IDEA_SCOPE + MIL_IDEA_SCOPE
ALL_IDEA_COUNT = len(ALL_IDEA_NAMES)

# Check if all idea names are valid
for idea_name in ALL_IDEA_NAMES:
    if idea_name not in IDEAS:
        logging.critical(f'Idea {idea_name} not found!')
        exit()


def get_score(effects: dict, weights: list[dict]):
    score = 0
    for weight in weights:
        for key, value in weight.items():
            if key in effects:
                score += value * min(effects[key], LIMITS[key])
    return score


def get_development_effect(effects):
    return effects['development_cost'] + effects['development_cost_in_primary_culture']


def get_adm_tech_effect(effects):
    return effects['adm_tech_cost_modifier'] + effects['technology_cost']


def get_dip_tech_effect(effects):
    return effects['dip_tech_cost_modifier'] + effects['technology_cost']


def get_mil_tech_effect(effects):
    return effects['mil_tech_cost_modifier'] + effects['technology_cost']


def get_idea_effect(effects):
    return effects['idea_cost']

########################################################################
### Pre-compute ########################################################
########################################################################


logging.info('Pre-computing...')

IDEA_SCORE = {}
for idea_name in ALL_IDEA_NAMES:
    idea = IDEAS[idea_name]
    score = get_score(
        idea.effect, 
        [COUNTRY_WEIGHTS, MILITARY_WEIGHTS]
        ) + IDEA_WEIGHTS.get(idea_name, 0)
    IDEA_SCORE[idea_name] = score

IDEA_POLICY_POTENTIAL = defaultdict(list)
for policy in POLICIES.values():
    req0, req1 = policy.req
    for req0_1 in req0:
        IDEA_POLICY_POTENTIAL[req0_1].append(policy)
    for req1_1 in req1:
        IDEA_POLICY_POTENTIAL[req1_1].append(policy)

IDEA_NOT_COMPATIBLE = defaultdict(list)
for idea_1, idea_2 in ADM_NOT_COMPATIBLE + DIP_NOT_COMPATIBLE + MIL_NOT_COMPATIBLE:
    IDEA_NOT_COMPATIBLE[idea_1].append(idea_2)
    IDEA_NOT_COMPATIBLE[idea_2].append(idea_1)

POLICY_LIB = {}
for policy in POLICIES.values():
    req0, req1 = policy.req
    for req0_1 in req0:
        for req1_1 in req1:
            policy_id = tuple(sorted([req0_1, req1_1]))
            POLICY_LIB[policy_id] = policy

POLICY_WAR_SCORE = {}
for policy in POLICIES.values():
    score = get_score(policy.effect, [MILITARY_WEIGHTS])
    POLICY_WAR_SCORE[policy.name] = score

DEV_POLICY_SET = set([policy.name for policy in POLICIES.values() if policy.effect.get(
    'development_cost', 0) != 0 or policy.effect.get('development_cost_in_primary_culture', 0) != 0])
ADM_TECH_POLICY_SET = set([policy.name for policy in POLICIES.values() if policy.effect.get(
    'adm_tech_cost_modifier', 0) != 0 or policy.effect.get('technology_cost', 0) != 0])
DIP_TECH_POLICY_SET = set([policy.name for policy in POLICIES.values() if policy.effect.get(
    'dip_tech_cost_modifier', 0) != 0 or policy.effect.get('technology_cost', 0) != 0])
MIL_TECH_POLICY_SET = set([policy.name for policy in POLICIES.values() if policy.effect.get(
    'mil_tech_cost_modifier', 0) != 0 or policy.effect.get('technology_cost', 0) != 0])
IDEA_POLICY_SET = set([policy.name for policy in POLICIES.values(
) if policy.effect.get('idea_cost', 0) != 0])


########################################################################
### Potential filtering ################################################
########################################################################

if args.force:
    logging.info('Consider not forcing and using potential filtering!')
    potential_filtering = 0
else:
    idea_potential_score = {}
    for idea_name in ALL_IDEA_NAMES:
        idea = IDEAS[idea_name]
        idea_potential_score[idea_name] = get_score(
            idea.effect, [COUNTRY_WEIGHTS, MILITARY_WEIGHTS]) + IDEA_WEIGHTS.get(idea_name, 0)
    idea_policies_potential_score = Counter()
    for idea_name in ALL_IDEA_NAMES:
        available_policies = [policy for policy in POLICIES.values(
        ) if idea_name in policy.req[0] or idea_name in policy.req[1]]
        for policy in available_policies:
            idea_policies_potential_score[idea_name] += get_score(
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
                 f' 10% percentile: {np.quantile(combined_potential_scores, 0.1):.2f}, \n'
                 f' 25% percentile: {np.quantile(combined_potential_scores, 0.25):.2f}, \n'
                 f' 40% percentile: {np.quantile(combined_potential_scores, 0.4):.2f}, \n'
                 f' 50% percentile: {np.quantile(combined_potential_scores, 0.5):.2f}, \n'
                 f' 60% percentile: {np.quantile(combined_potential_scores, 0.6):.2f}, \n'
                 f' 75% percentile: {np.quantile(combined_potential_scores, 0.75):.2f}, \n'
                 f' 90% percentile: {np.quantile(combined_potential_scores, 0.9):.2f}')

    logging.debug(f'Idea potential scores: {combined_potential_score}')

    if args.potential_filtering is None:
        potential_filtering = input(
            'Enter potential threshold in percent (0-100): [25] ')
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
        idea_name for idea_name in ADM_IDEA_SCOPE
        if combined_potential_score[idea_name] >= potential_threshold
    ]
    DIP_IDEA_SCOPE = [
        idea_name for idea_name in DIP_IDEA_SCOPE
        if combined_potential_score[idea_name] >= potential_threshold
    ]
    MIL_IDEA_SCOPE = [
        idea_name for idea_name in MIL_IDEA_SCOPE
        if combined_potential_score[idea_name] >= potential_threshold
    ]
    ideas_to_be_filtered_out = [
        idea_name for idea_name in ALL_IDEA_NAMES
        if combined_potential_score[idea_name] < potential_threshold
    ]
    logging.debug(f'Ideas to be filtered out: {ideas_to_be_filtered_out}')

########################################################################
### Build tools ########################################################
########################################################################


def deepcopy(obj):
    # return copy.deepcopy(obj)
    return pickle.loads(pickle.dumps(obj))


def get_total_effect(build: Build):
    total_effect = Counter()
    total_effect.update(build.ideas_effect)

    adm_max_policies = build.max_policies[0] + \
        build.ideas_effect['possible_policy'] + \
        build.ideas_effect['possible_adm_policy']
    dip_max_policies = build.max_policies[1] + \
        build.ideas_effect['possible_policy'] + \
        build.ideas_effect['possible_dip_policy']
    mil_max_policies = build.max_policies[2] + \
        build.ideas_effect['possible_policy'] + \
        build.ideas_effect['possible_mil_policy']

    active_policies = []
    # War policies
    active_policies.extend(build.war_policies[0][:adm_max_policies])
    active_policies.extend(build.war_policies[1][:dip_max_policies])
    active_policies.extend(build.war_policies[2][:mil_max_policies])
    # Dev policies
    active_policies.extend(build.dev_policies[0][:adm_max_policies])
    active_policies.extend(build.dev_policies[1][:dip_max_policies])
    active_policies.extend(build.dev_policies[2][:mil_max_policies])
    # Adm tech policies
    active_policies.extend(build.adm_tech_policies[0][:adm_max_policies])
    active_policies.extend(build.adm_tech_policies[1][:dip_max_policies])
    active_policies.extend(build.adm_tech_policies[2][:mil_max_policies])
    # Dip tech policies
    active_policies.extend(build.dip_tech_policies[0][:adm_max_policies])
    active_policies.extend(build.dip_tech_policies[1][:dip_max_policies])
    active_policies.extend(build.dip_tech_policies[2][:mil_max_policies])
    # Mil tech policies
    active_policies.extend(build.mil_tech_policies[0][:adm_max_policies])
    active_policies.extend(build.mil_tech_policies[1][:dip_max_policies])
    active_policies.extend(build.mil_tech_policies[2][:mil_max_policies])
    # Idea policies
    active_policies.extend(build.idea_policies[0][:adm_max_policies])
    active_policies.extend(build.idea_policies[1][:dip_max_policies])
    active_policies.extend(build.idea_policies[2][:mil_max_policies])

    for policy in active_policies:
        total_effect.update(POLICIES[policy[1]].effect)

    return total_effect


def expanded_build(build: Build, idea_name: str,) -> Build:
    idea = IDEAS[idea_name]

    # Update Idea counts

    idea_counts = (
        build.idea_counts[0] + (idea_name in ADM_IDEA_SCOPE),
        build.idea_counts[1] + (idea_name in DIP_IDEA_SCOPE),
        build.idea_counts[2] + (idea_name in MIL_IDEA_SCOPE),
    )

    # Expand build with new idea

    idea_set = build.idea_set.copy()
    idea_set.add(idea_name)

    cum_idea_score = build.cum_idea_score + IDEA_SCORE[idea_name]

    ideas_effect = build.ideas_effect.copy()
    ideas_effect.update(idea.effect)

    # Check for new available policies and place them in order of importance

    def update_policies(build: Build):
        policy_set = build.policy_set.copy()
        war_policies = deepcopy(build.war_policies)
        dev_policies = deepcopy(build.dev_policies)
        adm_tech_policies = deepcopy(build.adm_tech_policies)
        dip_tech_policies = deepcopy(build.dip_tech_policies)
        mil_tech_policies = deepcopy(build.mil_tech_policies)
        idea_policies = deepcopy(build.idea_policies)

        for build_idea in build.idea_set:
            policy_id = tuple(sorted([build_idea, idea_name]))
            if (policy := POLICY_LIB.get(policy_id)) and policy.name not in policy_set:
                policy_set.add(policy.name)
                policy_war_score = POLICY_WAR_SCORE[policy.name]
                policy_dev_effect = get_development_effect(policy.effect)
                policy_adm_tech_effect = get_adm_tech_effect(policy.effect)
                policy_dip_tech_effect = get_dip_tech_effect(policy.effect)
                policy_mil_tech_effect = get_mil_tech_effect(policy.effect)
                policy_idea_effect = get_idea_effect(policy.effect)
                if policy.type in Build.POLICY_TYPE_INDEX:
                    policy_index = Build.POLICY_TYPE_INDEX[policy.type]
                    if policy_war_score > 0:
                        bisect.insort(
                            war_policies[policy_index],
                            (policy_war_score, policy.name),
                            key=lambda x: -1 * x[0]
                        )
                    if policy_dev_effect > 0:
                        bisect.insort(
                            dev_policies[policy_index],
                            (policy_dev_effect, policy.name),
                            key=lambda x: -1 * x[0]
                        )
                    if policy_adm_tech_effect > 0:
                        bisect.insort(
                            adm_tech_policies[policy_index],
                            (policy_adm_tech_effect, policy.name),
                            key=lambda x: -1 * x[0]
                        )
                    if policy_dip_tech_effect > 0:
                        bisect.insort(
                            dip_tech_policies[policy_index],
                            (policy_dip_tech_effect, policy.name),
                            key=lambda x: -1 * x[0]
                        )
                    if policy_mil_tech_effect > 0:
                        bisect.insort(
                            mil_tech_policies[policy_index],
                            (policy_mil_tech_effect, policy.name),
                            key=lambda x: -1 * x[0]
                        )
                    if policy_idea_effect > 0:
                        bisect.insort(
                            idea_policies[policy_index],
                            (policy_idea_effect, policy.name),
                            key=lambda x: -1 * x[0]
                        )
        return (
            policy_set,
            war_policies,
            dev_policies,
            adm_tech_policies,
            dip_tech_policies,
            mil_tech_policies,
            idea_policies,
        )

    policy_set, \
        war_policies, \
        dev_policies, \
        adm_tech_policies, \
        dip_tech_policies, \
        mil_tech_policies, \
        idea_policies \
        = update_policies(build)

    # Create policy micro management effects

    adm_max_policies = build.max_policies[0] + \
        ideas_effect['possible_policy'] + ideas_effect['possible_adm_policy']
    dip_max_policies = build.max_policies[1] + \
        ideas_effect['possible_policy'] + ideas_effect['possible_dip_policy']
    mil_max_policies = build.max_policies[2] + \
        ideas_effect['possible_policy'] + ideas_effect['possible_mil_policy']

    total_dev_effect = sum([policy[0] for policy in dev_policies[0][:adm_max_policies]]) + \
        sum([policy[0] for policy in dev_policies[1][:dip_max_policies]]) + \
        sum([policy[0] for policy in dev_policies[2][:mil_max_policies]])
    total_adm_tech_effect = sum([policy[0] for policy in adm_tech_policies[0][:adm_max_policies]]) + \
        sum([policy[0] for policy in adm_tech_policies[1][:dip_max_policies]]) + \
        sum([policy[0] for policy in adm_tech_policies[2][:mil_max_policies]])
    total_dip_tech_effect = sum([policy[0] for policy in dip_tech_policies[0][:adm_max_policies]]) + \
        sum([policy[0] for policy in dip_tech_policies[1][:dip_max_policies]]) + \
        sum([policy[0] for policy in dip_tech_policies[2][:mil_max_policies]])
    total_ida_effect = sum([policy[0] for policy in idea_policies[0][:adm_max_policies]]) + \
        sum([policy[0] for policy in idea_policies[1][:dip_max_policies]]) + \
        sum([policy[0] for policy in idea_policies[2][:mil_max_policies]])

    micro_policy_effect = Counter()
    micro_policy_effect['development_cost'] = total_dev_effect
    micro_policy_effect['adm_tech_cost_modifier'] = total_adm_tech_effect
    micro_policy_effect['dip_tech_cost_modifier'] = total_dip_tech_effect
    micro_policy_effect['mil_tech_cost_modifier'] = total_dip_tech_effect
    micro_policy_effect['idea_cost'] = total_ida_effect

    # Create policy war effects

    war_policy_effect = Counter()
    for policy in war_policies[0][:adm_max_policies]:
        war_policy_effect.update(POLICIES[policy[1]].effect)
    for policy in war_policies[1][:dip_max_policies]:
        war_policy_effect.update(POLICIES[policy[1]].effect)
    for policy in war_policies[2][:mil_max_policies]:
        war_policy_effect.update(POLICIES[policy[1]].effect)

    # Calculate total score

    total_score = cum_idea_score + \
        get_score(micro_policy_effect, [COUNTRY_WEIGHTS]) + \
        get_score(war_policy_effect, [MILITARY_WEIGHTS])

    return Build(
        idea_set=idea_set,
        idea_counts=idea_counts,
        cum_idea_score=cum_idea_score,
        ideas_effect=ideas_effect,
        policy_set=policy_set,
        max_policies=build.max_policies,
        war_policies=war_policies,
        dev_policies=dev_policies,
        adm_tech_policies=adm_tech_policies,
        dip_tech_policies=dip_tech_policies,
        mil_tech_policies=mil_tech_policies,
        idea_policies=idea_policies,
        total_score=total_score,
    )


def iter_expanding_ideas(build: Build, idea_count_threshold=0.39) -> str:
    adm_idea_count, dip_idea_count, mil_idea_count = build.idea_counts
    idea_count = adm_idea_count + dip_idea_count + mil_idea_count
    if adm_idea_count / idea_count < idea_count_threshold:
        for idea_name in ADM_IDEA_SCOPE:
            if idea_name not in build.idea_set:
                for idea_conflict in IDEA_NOT_COMPATIBLE[idea_name]:
                    if idea_conflict in build.idea_set:
                        break
                else:
                    yield idea_name
    if dip_idea_count / idea_count < idea_count_threshold:
        for idea_name in DIP_IDEA_SCOPE:
            if idea_name not in build.idea_set:
                for idea_conflict in IDEA_NOT_COMPATIBLE[idea_name]:
                    if idea_conflict in build.idea_set:
                        break
                else:
                    yield idea_name
    if mil_idea_count / idea_count < idea_count_threshold:
        for idea_name in MIL_IDEA_SCOPE:
            if idea_name not in build.idea_set:
                for idea_conflict in IDEA_NOT_COMPATIBLE[idea_name]:
                    if idea_conflict in build.idea_set:
                        break
                else:
                    yield idea_name


def get_ideas_to_expand(build_list: list[Build], best_n, random_n):
    build_list.sort(key=lambda x: x.total_score, reverse=True)
    best_builds = build_list[:best_n]
    random_builds = random.sample(
        build_list[best_n:], min(random_n, len(build_list[best_n:])))
    return best_builds + random_builds


def dump_builds_to_yaml(builds: list[Build], output_file_name: str, count: int = 100, highlights: list[str] = HIGHLIGHTS):
    data = []
    for build in builds[:count]:
        build_total_effect = get_total_effect(build)
        build_data = {
            'score': build.total_score,
            'ideas': list(build.idea_set),
            'main': {highlight: round(build_total_effect.get(highlight, 0), 3) for highlight in highlights},
            'other': {effect: round(value, 3) for effect, value in build_total_effect.items() if effect not in highlights}
        }
        data.append(build_data)

    with open(output_file_name, 'w') as f:
        yaml.dump(data, f)

########################################################################
### Gen README #########################################################
########################################################################


readme = f'''
# Build: {build_config_name.replace('_', ' ')}

- Created: {datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")}
- Religions: {args.religion}
- Governments: {args.gov}
- Empire: {args.empire}
- Potential filtering: {potential_filtering}

## Potential filtering

- mean: {combined_potential_scores.mean():.2f}
- std: {combined_potential_scores.std():.2f}
- min: {combined_potential_scores.min():.2f}
- max: {combined_potential_scores.max():.2f}
- 10% percentile: {np.quantile(combined_potential_scores, 0.1):.2f}
- 25% percentile: {np.quantile(combined_potential_scores, 0.25):.2f}
- 40% percentile: {np.quantile(combined_potential_scores, 0.4):.2f}
- 50% percentile: {np.quantile(combined_potential_scores, 0.5):.2f}
- 60% percentile: {np.quantile(combined_potential_scores, 0.6):.2f}
- 75% percentile: {np.quantile(combined_potential_scores, 0.75):.2f}
- 90% percentile: {np.quantile(combined_potential_scores, 0.9):.2f}

## Weights

- Country: 
```
{yaml.dump(COUNTRY_WEIGHTS, sort_keys=False)}
```
- Military: 
```
{yaml.dump(MILITARY_WEIGHTS, sort_keys=False)}
```
- Ideas: 
```
{yaml.dump(IDEA_WEIGHTS, sort_keys=False)}
```
'''

with open(os.path.join(OUTPUT_FOLDER_PATH, 'README.md'), 'w') as f:
    f.write(readme)

########################################################################
### Main ###############################################################
########################################################################

total_options = len(ADM_IDEA_SCOPE) * len(DIP_IDEA_SCOPE) * len(MIL_IDEA_SCOPE)
init_builds = []
with tqdm(total=total_options, desc='Creating the init 3 idea sets:') as pbar:
    for adm_idea in ADM_IDEA_SCOPE:
        base_adm_build = expanded_build(Build(), adm_idea)
        for dip_idea in DIP_IDEA_SCOPE:
            base_dip_build = expanded_build(base_adm_build, dip_idea)
            for mil_idea in MIL_IDEA_SCOPE:
                base_mil_build = expanded_build(base_dip_build, mil_idea)
                init_builds.append(base_mil_build)
                pbar.update(1)

expanded_builds = init_builds
for i in range(4, args.ideas + 1):
    builds_to_expand = list(expanded_builds)
    expanded_builds = []
    explored_builds = set()
    for build in tqdm(builds_to_expand, desc=f'Searching for {i} ideas:'):
        for idea_name in iter_expanding_ideas(build):
            build_idea_set = set(build.idea_set)
            build_idea_set.add(idea_name)
            build_id = '-'.join(sorted(list(build_idea_set)))
            if build_id not in explored_builds:
                expanded_builds.append(expanded_build(build, idea_name))
                explored_builds.add(build_id)
            # TODO: implement reservoir_sampling
            # if i >= args.exp_from and len(expanded_builds) >= 2 * (args.exp_top + args.exp_rand):
            #     expanded_builds.sort(key=lambda x: x.total_score, reverse=True)
            #     expanded_builds = expanded_builds[:args.exp_top + args.exp_rand]

    expanded_builds.sort(key=lambda x: x.total_score, reverse=True)
    if i >= args.exp_from:
        expanded_builds = get_ideas_to_expand(
            expanded_builds, best_n=args.exp_top, random_n=args.exp_rand)
    dump_builds_to_yaml(expanded_builds, os.path.join(
        OUTPUT_FOLDER_PATH, f'builds_{i}.yaml'), count=200)

########################################################################
### Stats ##############################################################
########################################################################

end_time = datetime.datetime.now()
elapsed_time = end_time - start_time
elapsed_minutes = elapsed_time.total_seconds() / 60
logging.info(f'Elapsed time: {elapsed_minutes:.2f} minutes')
