from functools import lru_cache
from collections import Counter
import itertools

from .model import Policy, Idea

def score(effects: dict, weights: list[dict], debug=False):
    score = 0
    for weight in weights:
        for key, value in effects.items():
            if key in weight:
                if debug:
                    print(f'{key}: {value} -> {value * weight[key]}')
                score += value * weight[key]
    return score

def get_ideas_effect(ideas: tuple[str], idea_pool: dict[str, Idea]):
    total_effect = Counter()
    for idea in ideas:
        total_effect.update(idea_pool[idea].effect)
        
    return total_effect

def get_available_policies(ideas: tuple[str], policies: list[Policy]):
    policy_pool = []
    for policy in policies:
       for idea_A, idea_B in itertools.combinations(ideas, 2):
            if idea_A in policy.req[0] and idea_B in policy.req[1]:
                policy_pool.append(policy)
                break
            elif idea_A in policy.req[1] and idea_B in policy.req[0]:
                policy_pool.append(policy)
                break
    policies_pool_adm = [p for p in policy_pool if p.type == 'ADM']
    policies_pool_dip = [p for p in policy_pool if p.type == 'DIP']
    policies_pool_mil = [p for p in policy_pool if p.type == 'MIL']
    return policies_pool_adm, policies_pool_dip, policies_pool_mil

def get_max_policy_slots(ideas_effect: Counter, base=4):
    adm_max_policy = base + ideas_effect['possible_policy'] + ideas_effect['possible_adm_policy']
    dip_max_policy = base + ideas_effect['possible_policy'] + ideas_effect['possible_dip_policy']
    mil_max_policy = base + ideas_effect['possible_policy'] + ideas_effect['possible_mil_policy']
    return adm_max_policy, dip_max_policy, mil_max_policy


def get_micro_management_policies_effect(ideas: tuple[str], available_policies: tuple[list[Policy], list[Policy], list[Policy]], max_policy_slots: tuple[int, int, int]):
    def get_max_effect(policies: list[Policy], effects: set[str], max_policies: int):
        effect_policies = [max(p.effect.get(effect, 0) for effect in effects) for p in policies if any(e in p.effect for e in effects)]
        effect_policies.sort(reverse=True)
        return sum(effect_policies[:max_policies])


    adm_max_policy, dip_max_policy, mil_max_policy = max_policy_slots
    available_adm_policies, available_dip_policies, available_mil_policies = available_policies

    total_effect = Counter()

    # Potential dev_cost policies 
    policy_dev_cost = 0
    dev_effects = {'development_cost'}
    policy_dev_cost += get_max_effect(available_adm_policies, dev_effects, adm_max_policy)
    policy_dev_cost += get_max_effect(available_dip_policies, dev_effects, dip_max_policy)
    policy_dev_cost += get_max_effect(available_mil_policies, dev_effects, mil_max_policy)
    total_effect['development_cost'] += policy_dev_cost

    # Potential tech cost policies
    adm_tech_cost_modifier = 0
    adm_tech_effects = {'technology_cost', 'adm_tech_cost_modifier'} 
    adm_tech_cost_modifier += get_max_effect(available_adm_policies, adm_tech_effects, adm_max_policy)
    adm_tech_cost_modifier += get_max_effect(available_dip_policies, adm_tech_effects, dip_max_policy)
    adm_tech_cost_modifier += get_max_effect(available_mil_policies, adm_tech_effects, mil_max_policy)
    total_effect['adm_tech_cost_modifier'] += adm_tech_cost_modifier
    
    dip_tech_cost_modifier = 0
    dip_tech_effects = {'technology_cost', 'dip_tech_cost_modifier'}
    dip_tech_cost_modifier += get_max_effect(available_adm_policies, dip_tech_effects, adm_max_policy)
    dip_tech_cost_modifier += get_max_effect(available_dip_policies, dip_tech_effects, dip_max_policy)
    dip_tech_cost_modifier += get_max_effect(available_mil_policies, dip_tech_effects, mil_max_policy)
    total_effect['dip_tech_cost_modifier'] += dip_tech_cost_modifier

    mil_tech_cost_modifier = 0
    mil_tech_effects = {'technology_cost', 'mil_tech_cost_modifier'}
    mil_tech_cost_modifier += get_max_effect(available_adm_policies, mil_tech_effects, adm_max_policy)
    mil_tech_cost_modifier += get_max_effect(available_dip_policies, mil_tech_effects, dip_max_policy)
    mil_tech_cost_modifier += get_max_effect(available_mil_policies, mil_tech_effects, mil_max_policy)
    total_effect['mil_tech_cost_modifier'] += mil_tech_cost_modifier

    # Potential idea cost policies
    policy_idea_cost = 0
    idea_effects = {'idea_cost'}
    policy_idea_cost += get_max_effect(available_adm_policies, idea_effects, adm_max_policy)
    policy_idea_cost += get_max_effect(available_dip_policies, idea_effects, dip_max_policy)
    policy_idea_cost += get_max_effect(available_mil_policies, idea_effects, mil_max_policy)
    total_effect['idea_cost'] += policy_idea_cost

    return total_effect

def get_war_policies_effect(ideas: tuple[str], war_weights: dict, available_policies: tuple[list[Policy], list[Policy], list[Policy]], max_policy_slots: tuple[int, int, int]):
    adm_max_policy, dip_max_policy, mil_max_policy = max_policy_slots
    available_adm_policies, available_dip_policies, available_mil_policies = available_policies

    total_effect = Counter()
    
    # ADM policy slots
    adm_war_policies = [(score(p.effect, [war_weights]), p) for p in available_adm_policies]
    adm_war_policies.sort(key=lambda x: x[0], reverse=True)
    adm_war_policies = [p for p in adm_war_policies if p[0] > 0]
    for p in adm_war_policies[:min(adm_max_policy, len(adm_war_policies))]:
        total_effect.update(p[1].effect)

    # DIP war policies
    dip_war_policies = [(score(p.effect, [war_weights]), p) for p in available_dip_policies]
    dip_war_policies.sort(key=lambda x: x[0], reverse=True)
    dip_war_policies = [p for p in dip_war_policies if p[0] > 0]
    for p in dip_war_policies[:min(dip_max_policy, len(dip_war_policies))]:
        total_effect.update(p[1].effect)

    # MIL war policies
    mil_war_policies = [(score(p.effect, [war_weights]), p) for p in available_mil_policies]
    mil_war_policies.sort(key=lambda x: x[0], reverse=True)
    mil_war_policies = [p for p in mil_war_policies if p[0] > 0]
    for p in mil_war_policies[:min(mil_max_policy, len(mil_war_policies))]:
        total_effect.update(p[1].effect)

    return total_effect
