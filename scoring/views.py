from django.contrib import messages
from django.db.models import Q
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse
from django.views.decorators.http import require_http_methods

from .forms import PlayerForm, ScoreEntryForm, ScorekeeperLoginForm
from .models import EventCategory, Game, Player, ScoreEntry, ScorekeeperAccount, Team
from .standings import build_game_points_tables, build_team_standings, entry_points


def home(request):
    query = request.GET.get("q", "").strip()
    players = []
    teams = []
    if query:
        players = Player.objects.select_related("team").filter(
            Q(name__icontains=query) | Q(team__name__icontains=query)
        )[:30]
        teams = Team.objects.filter(name__icontains=query)[:12]

    active_games = list(Game.objects.filter(active=True).order_by("category", "sort_order", "name"))
    category_groups = {}
    for category, label in EventCategory.choices:
        category_groups[category] = {
            "label": label,
            "games": [game for game in active_games if game.category == category],
        }

    scores = list(
        ScoreEntry.objects.select_related("game", "team", "player1", "player2")
        .filter(game__active=True, team__isnull=False)
        .order_by("game__category", "game__sort_order", "rank", "-score", "recorded_at")
    )
    scores_by_game = {}
    for entry in scores:
        scores_by_game.setdefault(entry.game_id, []).append(entry)

    recent_scores = ScoreEntry.objects.select_related("game", "team", "player1", "player2").order_by("-updated_at")[:12]

    return render(
        request,
        "scoring/home.html",
        {
            "query": query,
            "players": players,
            "teams": teams,
            "category_groups": category_groups,
            "team_standings": build_team_standings(scores),
            "game_points_tables": build_game_points_tables(active_games, scores_by_game),
            "recent_scores": recent_scores,
        },
    )


def player_detail(request, pk):
    player = get_object_or_404(Player.objects.select_related("team"), pk=pk)
    personal_scores = ScoreEntry.objects.select_related("game", "team", "player1", "player2").filter(
        Q(player1=player) | Q(player2=player)
    )
    team_scores = ScoreEntry.objects.select_related("game", "team").filter(team=player.team) if player.team else []
    return render(
        request,
        "scoring/player_detail.html",
        {"player": player, "personal_scores": personal_scores, "team_scores": team_scores},
    )


def team_detail(request, pk):
    team = get_object_or_404(Team, pk=pk)
    roster = team.players.order_by("name")
    scores = team.scores.select_related("game").order_by("game__sort_order", "rank", "-score")
    rows = [{"entry": score, "points": entry_points(score)} for score in scores]
    total_points = sum(row["points"] for row in rows)
    return render(
        request,
        "scoring/team_detail.html",
        {"team": team, "roster": roster, "scores": scores, "score_rows": rows, "total_points": total_points},
    )


def _current_scorekeeper(request):
    account_id = request.session.get("scorekeeper_id")
    if not account_id:
        return None
    return ScorekeeperAccount.objects.filter(pk=account_id, active=True).first()


@require_http_methods(["GET", "POST"])
def scorekeeper_login(request):
    if request.method == "POST":
        form = ScorekeeperLoginForm(request.POST)
        if form.is_valid():
            account = ScorekeeperAccount.objects.filter(
                username=form.cleaned_data["username"].strip(),
                active=True,
            ).first()
            if account and account.check_password(form.cleaned_data["password"]):
                request.session["scorekeeper_id"] = account.pk
                return redirect("scoring:scorekeeper_dashboard")
            messages.error(request, "Invalid scorekeeper ID or password.")
    else:
        form = ScorekeeperLoginForm()
    return render(request, "scoring/scorekeeper_login.html", {"form": form})


def scorekeeper_logout(request):
    request.session.pop("scorekeeper_id", None)
    return redirect("scoring:home")


def scorekeeper_dashboard(request):
    account = _current_scorekeeper(request)
    if not account:
        return redirect(f"{reverse('scoring:scorekeeper_login')}?next={request.path}")
    games = account.games.filter(active=True).order_by("category", "sort_order", "name")
    return render(request, "scoring/scorekeeper_dashboard.html", {"account": account, "games": games})


@require_http_methods(["GET", "POST"])
def scorekeeper_game(request, slug):
    account = _current_scorekeeper(request)
    if not account:
        return redirect(f"{reverse('scoring:scorekeeper_login')}?next={request.path}")
    game = get_object_or_404(account.games.filter(active=True), slug=slug)

    score_form = ScoreEntryForm(game=game)
    player_form = PlayerForm()

    if request.method == "POST":
        if request.POST.get("action") == "add_player":
            player_form = PlayerForm(request.POST)
            if player_form.is_valid():
                player = player_form.save()
                messages.success(request, f"Added {player.name}.")
                return redirect("scoring:scorekeeper_game", slug=game.slug)
        else:
            score_form = ScoreEntryForm(request.POST, game=game)
            if score_form.is_valid():
                score_form.save()
                messages.success(request, "Score saved.")
                return redirect("scoring:scorekeeper_game", slug=game.slug)

    scores = game.scores.select_related("team", "player1", "player2").order_by("rank", "-score", "-updated_at")
    return render(
        request,
        "scoring/scorekeeper_game.html",
        {
            "account": account,
            "game": game,
            "score_form": score_form,
            "player_form": player_form,
            "scores": scores,
        },
    )
