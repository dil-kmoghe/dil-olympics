from django.core.management.base import BaseCommand
from django.db import transaction

from scoring.models import Player, ScoreEntry, Team
from scoring.team_utils import canonical_team_name, group_teams_by_key, player_key


class Command(BaseCommand):
    help = "Merge teams that differ only by case, spacing, punctuation, or trailing import numbers."

    def handle(self, *args, **options):
        merged_groups = 0
        merged_teams = 0
        merged_players = 0

        with transaction.atomic():
            groups = group_teams_by_key(Team.objects.all())
            for teams in groups.values():
                if len(teams) < 2:
                    continue

                canonical_name = canonical_team_name([team.name for team in teams])
                canonical = next((team for team in teams if team.name == canonical_name), teams[0])
                if canonical.name != canonical_name and not Team.objects.filter(name=canonical_name).exclude(pk=canonical.pk).exists():
                    canonical.name = canonical_name
                    canonical.save(update_fields=["name"])

                duplicates = [team for team in teams if team.pk != canonical.pk]
                for duplicate in duplicates:
                    if not canonical.colour and duplicate.colour:
                        canonical.colour = duplicate.colour
                        canonical.save(update_fields=["colour"])
                    Player.objects.filter(team=duplicate).update(team=canonical)
                    ScoreEntry.objects.filter(team=duplicate).update(team=canonical)
                    duplicate.delete()
                    merged_teams += 1

                merged_groups += 1
                self.stdout.write(f"Merged into '{canonical.name}': {', '.join(team.name for team in duplicates)}")

            for team in Team.objects.prefetch_related("players"):
                players_by_key = {}
                for player in team.players.order_by("created_at", "pk"):
                    key = player_key(player.name)
                    if not key:
                        continue
                    if key not in players_by_key:
                        players_by_key[key] = player
                        continue

                    canonical_player = players_by_key[key]
                    if not canonical_player.shirt_size and player.shirt_size:
                        canonical_player.shirt_size = player.shirt_size
                    if not canonical_player.shirt_colour and player.shirt_colour:
                        canonical_player.shirt_colour = player.shirt_colour
                    canonical_player.save(update_fields=["shirt_size", "shirt_colour"])
                    ScoreEntry.objects.filter(player1=player).update(player1=canonical_player)
                    ScoreEntry.objects.filter(player2=player).update(player2=canonical_player)
                    player.delete()
                    merged_players += 1

        self.stdout.write(
            self.style.SUCCESS(
                f"Merged {merged_teams} duplicate teams across {merged_groups} groups and {merged_players} duplicate players."
            )
        )
