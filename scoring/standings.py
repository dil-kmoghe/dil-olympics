POINTS_BY_RANK = {
    1: 10,
    2: 8,
    3: 6,
    4: 5,
    5: 4,
    6: 3,
    7: 2,
}


def points_for_rank(rank):
    if rank is None:
        return 0
    return POINTS_BY_RANK.get(rank, 1)


def entry_points(entry):
    return points_for_rank(entry.rank)


def build_game_points_tables(games, scores_by_game):
    tables = []
    for game in games:
        rows = []
        for entry in scores_by_game.get(game.pk, []):
            rows.append(
                {
                    "entry": entry,
                    "team": entry.team,
                    "rank": entry.rank,
                    "score": entry.score,
                    "points": entry_points(entry),
                }
            )
        tables.append({"game": game, "rows": rows})
    return tables


def build_team_standings(scores):
    best_points_by_team_game = {}
    games_played = {}

    for entry in scores:
        if not entry.team_id:
            continue
        key = (entry.team_id, entry.game_id)
        best_points_by_team_game[key] = max(best_points_by_team_game.get(key, 0), entry_points(entry))
        games_played.setdefault(entry.team_id, set()).add(entry.game_id)

    teams = {entry.team_id: entry.team for entry in scores if entry.team_id}
    totals = {}
    for team_id, _game_id in best_points_by_team_game:
        totals[team_id] = totals.get(team_id, 0) + best_points_by_team_game[(team_id, _game_id)]

    standings = [
        {
            "team": teams[team_id],
            "games_played": len(games_played.get(team_id, set())),
            "total_points": points,
        }
        for team_id, points in totals.items()
    ]
    standings.sort(key=lambda row: (-row["total_points"], -row["games_played"], row["team"].name.lower()))
    return standings
