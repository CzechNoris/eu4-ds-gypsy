from collections import Counter, defaultdict
import bisect
import pickle


from model import Policy, Idea, Build


def get_policy_id(policy_a_name: str, policy_b_name: str):
    return tuple(sorted([policy_a_name, policy_b_name]))


def get_score(effects: dict, weights: list[dict]):
    score = 0
    for weight in weights:
        for key, value in weight.items():
            if key in effects:
                score += value * effects[key]
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


def get_ideas_effect(ideas: tuple[str], idea_pool: dict[str, Idea]):
    total_effect = Counter()
    for idea in ideas:
        total_effect.update(idea_pool[idea].effect)

    return total_effect


class BuildConst:
    def __init__(self,
                 ideas: dict[str, Idea],
                 policies: dict[str, Policy],
                 country_weights: dict[str, float],
                 military_weights: dict[str, float],
                 idea_weights: dict[str, float],
                 ):

        self.IDEAS = ideas
        self.POLICIES = policies
        self.COUNTRY_WEIGHTS = country_weights
        self.MILITARY_WEIGHTS = military_weights
        self.IDEA_WEIGHTS = idea_weights

        self.IDEA_SCORE = {}
        for idea_name, idea in ideas.items():
            score = get_score(
                idea.effect,
                [country_weights, military_weights]
            ) + idea_weights.get(idea_name, 0)
            self.IDEA_SCORE[idea_name] = score

        self.IDEA_POLICY_POTENTIAL = defaultdict(list)
        for _, policy in policies.items():
            req0, req1 = policy.req
            for req0_1 in req0:
                self.IDEA_POLICY_POTENTIAL[req0_1].append(policy)
            for req1_1 in req1:
                self.IDEA_POLICY_POTENTIAL[req1_1].append(policy)

        self.POLICY_LIB = {}
        for _, policy in policies.items():
            req0, req1 = policy.req
            for req0_1 in req0:
                for req1_1 in req1:
                    policy_id = get_policy_id(req0_1, req1_1)
                    self.POLICY_LIB[policy_id] = policy

        self.POLICY_WAR_SCORE = {}
        for _, policy in policies.items():
            score = get_score(policy.effect, [military_weights])
            self.POLICY_WAR_SCORE[policy.name] = score

        self.DEV_POLICY_SET = set([
            policy.name for policy in policies.values()
            if policy.effect.get('development_cost', 0) != 0
            or policy.effect.get('development_cost_in_primary_culture', 0) != 0
        ])
        self.ADM_TECH_POLICY_SET = set([
            policy.name for policy in policies.values()
            if policy.effect.get('adm_tech_cost_modifier', 0) != 0
            or policy.effect.get('technology_cost', 0) != 0
        ])
        self.DIP_TECH_POLICY_SET = set([
            policy.name for policy in policies.values()
            if policy.effect.get('dip_tech_cost_modifier', 0) != 0
            or policy.effect.get('technology_cost', 0) != 0
        ])
        self.MIL_TECH_POLICY_SET = set([
            policy.name for policy in policies.values()
            if policy.effect.get('mil_tech_cost_modifier', 0) != 0
            or policy.effect.get('technology_cost', 0) != 0
        ])
        self.IDEA_POLICY_SET = set([
            policy.name for policy in policies.values()
            if policy.effect.get('idea_cost', 0) != 0
        ])


def expand_build(
    build: Build,
    idea_name: str,
    const: BuildConst,
) -> Build:
    
    def deepcopy(obj):
        return pickle.loads(pickle.dumps(obj))
    
    idea = const.IDEAS[idea_name]

    # Update Idea counts

    idea_counts = (
        build.idea_counts[0] + (idea.type == 'ADM'),
        build.idea_counts[1] + (idea.type == 'DIP'),
        build.idea_counts[2] + (idea.type == 'MIL'),
    )

    # Expand build with new idea

    idea_set = build.idea_set.copy()
    idea_set.add(idea_name)

    cum_idea_score = build.cum_idea_score + const.IDEA_SCORE[idea_name]

    ideas_effect = build.ideas_effect.copy()
    ideas_effect.update(idea.effect)

    # Check for new available policies and place them in order of importance

    policy_set = build.policy_set.copy()
    war_policies = copy.deepcopy(build.war_policies)
    dev_policies = copy.deepcopy(build.dev_policies)
    adm_tech_policies = copy.deepcopy(build.adm_tech_policies)
    dip_tech_policies = copy.deepcopy(build.dip_tech_policies)
    mil_tech_policies = copy.deepcopy(build.mil_tech_policies)
    idea_policies = copy.deepcopy(build.idea_policies)

    for build_idea in build.idea_set:
        policy_id = get_policy_id(idea_name, build_idea)
        if (policy := const.POLICY_LIB.get(policy_id)) and policy.name not in policy_set:
            policy_set.add(policy.name)
            policy_war_score = const.POLICY_WAR_SCORE[policy.name]
            policy_dev_effect = get_development_effect(policy.effect)
            policy_adm_tech_effect = get_adm_tech_effect(policy.effect)
            policy_dip_tech_effect = get_dip_tech_effect(policy.effect)
            policy_mil_tech_effect = get_mil_tech_effect(policy.effect)
            policy_idea_effect = get_idea_effect(policy.effect)
            if policy.type in Build.POLICY_TYPE_INDEX:
                policy_index = Build.POLICY_TYPE_INDEX.get(policy.type)
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

    # Get max policies counts

    adm_max_policies = \
        build.max_policies[0] + \
        ideas_effect['possible_policy'] + \
        ideas_effect['possible_adm_policy']
    dip_max_policies = \
        build.max_policies[1] + \
        ideas_effect['possible_policy'] + \
        ideas_effect['possible_dip_policy']
    mil_max_policies = \
        build.max_policies[2] + \
        ideas_effect['possible_policy'] + \
        ideas_effect['possible_mil_policy']

    # Create policy micro management effects

    total_dev_effect = \
        sum([policy[0] for policy in dev_policies[0][:adm_max_policies]]) + \
        sum([policy[0] for policy in dev_policies[1][:dip_max_policies]]) + \
        sum([policy[0] for policy in dev_policies[2][:mil_max_policies]])
    total_adm_tech_effect = \
        sum([policy[0] for policy in adm_tech_policies[0][:adm_max_policies]]) + \
        sum([policy[0] for policy in adm_tech_policies[1][:dip_max_policies]]) + \
        sum([policy[0] for policy in adm_tech_policies[2][:mil_max_policies]])
    total_dip_tech_effect = \
        sum([policy[0] for policy in dip_tech_policies[0][:adm_max_policies]]) + \
        sum([policy[0] for policy in dip_tech_policies[1][:dip_max_policies]]) + \
        sum([policy[0] for policy in dip_tech_policies[2][:mil_max_policies]])
    total_idea_effect = \
        sum([policy[0] for policy in idea_policies[0][:adm_max_policies]]) + \
        sum([policy[0] for policy in idea_policies[1][:dip_max_policies]]) + \
        sum([policy[0] for policy in idea_policies[2][:mil_max_policies]])

    micro_policy_effect = Counter()
    micro_policy_effect['development_cost'] = total_dev_effect
    micro_policy_effect['adm_tech_cost_modifier'] = total_adm_tech_effect
    micro_policy_effect['dip_tech_cost_modifier'] = total_dip_tech_effect
    micro_policy_effect['mil_tech_cost_modifier'] = total_dip_tech_effect
    micro_policy_effect['idea_cost'] = total_idea_effect

    # Create policy war effects

    war_policy_effect = Counter()
    for _, policy_name in war_policies[0][:adm_max_policies]:
        war_policy_effect.update(const.POLICIES[policy_name].effect)
    for _, policy_name in war_policies[1][:dip_max_policies]:
        war_policy_effect.update(const.POLICIES[policy_name].effect)
    for _, policy_name in war_policies[2][:mil_max_policies]:
        war_policy_effect.update(const.POLICIES[policy_name].effect)

    # Calculate total score

    total_score = cum_idea_score + \
        get_score(micro_policy_effect, [const.COUNTRY_WEIGHTS]) + \
        get_score(war_policy_effect, [const.MILITARY_WEIGHTS])

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

def get_total_effect(build: Build, policies: dict[str, Policy]):
    total_effect = Counter()
    total_effect.update(build.ideas_effect)
    
    adm_max_policies = build.max_policies[0] + build.ideas_effect['possible_policy'] + build.ideas_effect['possible_adm_policy']
    dip_max_policies = build.max_policies[1] + build.ideas_effect['possible_policy'] + build.ideas_effect['possible_dip_policy']
    mil_max_policies = build.max_policies[2] + build.ideas_effect['possible_policy'] + build.ideas_effect['possible_mil_policy']
    
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
        total_effect.update(policies[policy[1]].effect)
    
    return total_effect