import yaml
from collections import Counter

from .model import Idea, Policy


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
    policies = []
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
                    name = name, 
                    type = monarch_power, 
                    req = (req0, req1),
                    effect = effect
                )
    return policies