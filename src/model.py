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
        self.type = type
        self.req = req
        self.effect = effect

    def __repr__(self):
        return f"Policy({self.name}, {self.type}, {self.req}, {self.effect})"

class Build():
    def __init__(self, 
                 ideas: tuple[str], 
                 score: float, 
                 total_effect: Counter, 
                 war_policies_effect: dict
    ):
        self.ideas = ideas
        self.score = score
        self.total_effect = total_effect
        self.war_policies_effect = war_policies_effect

    def __repr__(self):
        return f"Build( {self.score:.2f} - ideas: {self.ideas})"