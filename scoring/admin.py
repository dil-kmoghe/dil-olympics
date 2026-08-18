from django.contrib import admin
from django.contrib import messages

from .forms import GameAdminForm, ScorekeeperAccountAdminForm
from .models import Game, Player, ScoreEntry, ScorekeeperAccount, Team


@admin.register(Team)
class TeamAdmin(admin.ModelAdmin):
    list_display = ["name", "colour", "player_count"]
    search_fields = ["name", "players__name"]

    def player_count(self, obj):
        return obj.players.count()


@admin.register(Player)
class PlayerAdmin(admin.ModelAdmin):
    list_display = ["name", "team", "shirt_size", "shirt_colour"]
    list_filter = ["team", "shirt_colour", "shirt_size"]
    search_fields = ["name", "team__name"]
    autocomplete_fields = ["team"]


@admin.register(Game)
class GameAdmin(admin.ModelAdmin):
    form = GameAdminForm
    list_display = ["name", "category", "active", "sort_order"]
    list_filter = ["category", "active"]
    search_fields = ["name"]
    prepopulated_fields = {"slug": ["name"]}
    fieldsets = (
        (None, {"fields": ("name", "slug", "category", "active", "sort_order", "scoring_notes")}),
        (
            "Scorekeeper login",
            {
                "fields": ("scorekeeper_username", "scorekeeper_password"),
                "description": "Optional. Fill these to create or attach a scorekeeper account for this game while saving.",
            },
        ),
    )

    def save_model(self, request, obj, form, change):
        super().save_model(request, obj, form, change)
        username = form.cleaned_data.get("scorekeeper_username")
        password = form.cleaned_data.get("scorekeeper_password")
        if not username:
            return

        account, created = ScorekeeperAccount.objects.get_or_create(username=username)
        if password:
            account.set_password(password)
        account.active = True
        account.save()
        account.games.add(obj)

        action = "Created" if created else "Updated"
        self.message_user(
            request,
            f"{action} scorekeeper '{account.username}' and assigned it to this game.",
            messages.SUCCESS,
        )


@admin.register(ScoreEntry)
class ScoreEntryAdmin(admin.ModelAdmin):
    list_display = ["game", "participant", "score", "rank", "updated_at"]
    list_filter = ["game__category", "game", "rank"]
    search_fields = ["game__name", "team__name", "player1__name", "player2__name", "notes"]
    autocomplete_fields = ["game", "team", "player1", "player2"]
    readonly_fields = ["rank", "recorded_at", "updated_at"]

    def participant(self, obj):
        return obj.participant_label


@admin.register(ScorekeeperAccount)
class ScorekeeperAccountAdmin(admin.ModelAdmin):
    form = ScorekeeperAccountAdminForm
    list_display = ["username", "active", "game_list", "created_at"]
    list_filter = ["active", "games"]
    search_fields = ["username", "games__name"]
    filter_horizontal = ["games"]
    readonly_fields = ["password_hash", "created_at"]

    def game_list(self, obj):
        return ", ".join(obj.games.values_list("name", flat=True)[:4])
