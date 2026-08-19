import re
from collections import defaultdict


def team_key(name):
    key = re.sub(r"[^a-z0-9]+", "", (name or "").lower())
    return re.sub(r"\d+$", "", key)


def player_key(name):
    return re.sub(r"[^a-z0-9]+", "", (name or "").lower())


def canonical_team_name(names):
    def score(name):
        stripped = name.strip()
        return (
            stripped[-1:].isdigit(),
            stripped.isupper(),
            "-" in stripped or "_" in stripped,
            not any(char.isspace() for char in stripped),
            len(stripped),
            stripped.lower(),
        )

    return sorted(names, key=score)[0].strip()


def group_teams_by_key(teams):
    groups = defaultdict(list)
    for team in teams:
        key = team_key(team.name)
        if key:
            groups[key].append(team)
    return groups
