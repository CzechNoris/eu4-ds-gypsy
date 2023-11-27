from collections import Counter


class Idea():
    def __init__(self, name:str, type: str, effect: dict):
        self.name = name
        self.type = type
        self.effect = effect

    def __repr__(self):
        return f'Idea({self.name}, {self.type}, {self.effect})'

class Policy():
    def __init__(self, name:str, type: str, req: tuple, effect: dict):
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
            war_policies: tuple[list[tuple[float, str]], list[tuple[float, str]], list[tuple[float, str]]] = None,
            dev_policies: tuple[list[tuple[float, str]], list[tuple[float, str]], list[tuple[float, str]]] = None,
            adm_tech_policies: tuple[list[tuple[float, str]], list[tuple[float, str]], list[tuple[float, str]]] = None,
            dip_tech_policies: tuple[list[tuple[float, str]], list[tuple[float, str]], list[tuple[float, str]]] = None,
            mil_tech_policies: tuple[list[tuple[float, str]], list[tuple[float, str]], list[tuple[float, str]]] = None,
            idea_policies: tuple[list[tuple[float, str]], list[tuple[float, str]], list[tuple[float, str]]] = None,
            total_score: float = 0,
        ):
        self.idea_set = idea_set if idea_set is not None else set()
        self.idea_counts = idea_counts if idea_counts is not None else (0, 0, 0)
        self.cum_idea_score = cum_idea_score if cum_idea_score is not None else 0
        self.ideas_effect = ideas_effect if ideas_effect is not None else Counter()
        self.policy_set = policy_set if policy_set is not None else set()
        self.max_policies = max_policies if max_policies is not None else (4, 4, 4)
        self.war_policies = war_policies if war_policies is not None else ([], [], [])
        self.dev_policies = dev_policies if dev_policies is not None else ([], [], [])
        self.adm_tech_policies = adm_tech_policies if adm_tech_policies is not None else ([], [], [])
        self.dip_tech_policies = dip_tech_policies if dip_tech_policies is not None else ([], [], [])
        self.mil_tech_policies = mil_tech_policies if mil_tech_policies is not None else ([], [], [])
        self.idea_policies = idea_policies if idea_policies is not None else ([], [], [])
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