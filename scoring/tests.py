from django.core.management import call_command
from django.test import TestCase
from django.urls import reverse
from django.contrib.auth import get_user_model

from .models import EventCategory, Game, ScoreEntry, ScorekeeperAccount, Team
from .standings import build_game_points_tables, build_team_standings


class ScorekeeperScoringTests(TestCase):
    def setUp(self):
        self.game = Game.objects.create(name="Paper Floor Relay", category=EventCategory.TEAM)
        self.team_a = Team.objects.create(name="Alpha")
        self.team_b = Team.objects.create(name="Bravo")
        self.account = ScorekeeperAccount.objects.create(username="scorekeeper")
        self.account.set_password("pass12345")
        self.account.save()
        self.account.games.add(self.game)

    def login_scorekeeper(self):
        self.client.post(
            reverse("scoring:scorekeeper_login"),
            {"username": "scorekeeper", "password": "pass12345"},
        )

    def test_scorekeeper_submits_team_only_score(self):
        self.login_scorekeeper()

        response = self.client.post(
            reverse("scoring:scorekeeper_game", args=[self.game.slug]),
            {"action": "score", "team": self.team_a.pk, "score": "15", "notes": "clean run"},
        )

        self.assertRedirects(response, reverse("scoring:scorekeeper_game", args=[self.game.slug]))
        score = ScoreEntry.objects.get(game=self.game, team=self.team_a)
        self.assertEqual(score.rank, 1)
        self.assertIsNone(score.player1)
        self.assertIsNone(score.player2)

    def test_ranks_recalculate_from_scores(self):
        ScoreEntry.objects.create(game=self.game, team=self.team_a, score=10)
        ScoreEntry.objects.create(game=self.game, team=self.team_b, score=20)

        self.assertEqual(ScoreEntry.objects.get(team=self.team_b).rank, 1)
        self.assertEqual(ScoreEntry.objects.get(team=self.team_a).rank, 2)

        ScoreEntry.objects.filter(team=self.team_a).update(score=25)
        score = ScoreEntry.objects.get(team=self.team_a)
        score.save()

        self.assertEqual(ScoreEntry.objects.get(team=self.team_a).rank, 1)
        self.assertEqual(ScoreEntry.objects.get(team=self.team_b).rank, 2)

    def test_standings_use_games_played_and_points(self):
        second_game = Game.objects.create(name="Spin Transfer", category=EventCategory.TEAM)
        ScoreEntry.objects.create(game=self.game, team=self.team_a, score=30)
        ScoreEntry.objects.create(game=self.game, team=self.team_b, score=20)
        ScoreEntry.objects.create(game=second_game, team=self.team_b, score=40)

        scores = list(ScoreEntry.objects.select_related("game", "team").order_by("game_id", "rank"))
        standings = build_team_standings(scores)
        tables = build_game_points_tables([self.game, second_game], {self.game.pk: scores[:2], second_game.pk: scores[2:]})

        self.assertEqual(standings[0]["team"], self.team_b)
        self.assertEqual(standings[0]["games_played"], 2)
        self.assertEqual(standings[0]["total_points"], 18)
        self.assertEqual(standings[1]["team"], self.team_a)
        self.assertEqual(standings[1]["games_played"], 1)
        self.assertEqual(standings[1]["total_points"], 10)
        self.assertEqual(tables[0]["rows"][0]["points"], 10)
        self.assertEqual(tables[0]["rows"][1]["points"], 8)


class GameAdminTests(TestCase):
    def setUp(self):
        User = get_user_model()
        self.admin_user = User.objects.create_superuser(username="admin", password="adminpass123")
        self.client.force_login(self.admin_user)

    def test_game_admin_can_create_scorekeeper_with_game(self):
        response = self.client.post(
            reverse("admin:scoring_game_add"),
            {
                "name": "New Desk Sprint",
                "slug": "new-desk-sprint",
                "category": EventCategory.TEAM,
                "active": "on",
                "sort_order": "99",
                "scoring_notes": "",
                "scorekeeper_username": "desk-sprint",
                "scorekeeper_password": "gamepass123",
                "_save": "Save",
            },
        )

        self.assertEqual(response.status_code, 302)
        game = Game.objects.get(slug="new-desk-sprint")
        account = ScorekeeperAccount.objects.get(username="desk-sprint")
        self.assertTrue(account.check_password("gamepass123"))
        self.assertIn(game, account.games.all())


class TeamMergeTests(TestCase):
    def test_merge_duplicate_teams_moves_players_and_scores(self):
        game = Game.objects.create(name="Desk Relay", category=EventCategory.TEAM)
        canonical = Team.objects.create(name="BE Awesome")
        duplicate = Team.objects.create(name="BE-AWESOME1")
        player = canonical.players.create(name="Maya Shinde")
        duplicate_player = duplicate.players.create(name="maya shinde")
        score = ScoreEntry.objects.create(game=game, team=duplicate, score=10)
        player_score = ScoreEntry.objects.create(game=game, team=duplicate, player1=duplicate_player, score=8)

        call_command("merge_duplicate_teams")

        self.assertTrue(Team.objects.filter(name="BE Awesome").exists())
        self.assertFalse(Team.objects.filter(name="BE-AWESOME1").exists())
        score.refresh_from_db()
        self.assertEqual(score.team, canonical)
        player_score.refresh_from_db()
        self.assertEqual(player_score.player1, player)
        self.assertEqual(canonical.players.count(), 1)
