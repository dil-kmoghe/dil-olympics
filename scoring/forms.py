from django import forms

from .models import Game, Player, ScoreEntry, ScorekeeperAccount, Team


class ScorekeeperLoginForm(forms.Form):
    username = forms.CharField(max_length=80)
    password = forms.CharField(widget=forms.PasswordInput)


class PlayerForm(forms.ModelForm):
    new_team_name = forms.CharField(required=False, label="New team name")

    class Meta:
        model = Player
        fields = ["name", "team", "new_team_name", "shirt_size", "shirt_colour"]

    def save(self, commit=True):
        player = super().save(commit=False)
        new_team_name = self.cleaned_data.get("new_team_name", "").strip()
        if new_team_name:
            player.team, _ = Team.objects.get_or_create(name=new_team_name)
        if commit:
            player.save()
        return player


class ScoreEntryForm(forms.ModelForm):
    class Meta:
        model = ScoreEntry
        fields = ["team", "score", "notes"]
        widgets = {
            "notes": forms.TextInput(attrs={"placeholder": "Time, distance, fouls, or tie notes"}),
        }

    def __init__(self, *args, game: Game, **kwargs):
        self.game = game
        super().__init__(*args, **kwargs)
        self.fields["team"].required = True
        self.fields["team"].queryset = Team.objects.order_by("name")

    def save(self, commit=True):
        entry = super().save(commit=False)
        entry.game = self.game

        if commit:
            entry.full_clean()
            entry.save()
        return entry


class GameAdminForm(forms.ModelForm):
    scorekeeper_username = forms.CharField(
        required=False,
        max_length=80,
        help_text="Optional. Create or update a scorekeeper login for this game.",
    )
    scorekeeper_password = forms.CharField(
        required=False,
        widget=forms.PasswordInput(render_value=False),
        help_text="Required only when adding a new scorekeeper username.",
    )

    class Meta:
        model = Game
        fields = ["name", "slug", "category", "active", "sort_order", "scoring_notes"]

    def clean_scorekeeper_username(self):
        return self.cleaned_data.get("scorekeeper_username", "").strip()

    def clean(self):
        cleaned = super().clean()
        username = cleaned.get("scorekeeper_username")
        password = cleaned.get("scorekeeper_password")
        if username and not password and not ScorekeeperAccount.objects.filter(username=username).exists():
            self.add_error("scorekeeper_password", "Password is required for a new scorekeeper.")
        if password and not username:
            self.add_error("scorekeeper_username", "Username is required when setting a scorekeeper password.")
        return cleaned


class ScorekeeperAccountAdminForm(forms.ModelForm):
    password = forms.CharField(
        required=False,
        widget=forms.PasswordInput(render_value=False),
        help_text="Set this when creating or changing a scorekeeper password.",
    )

    class Meta:
        model = ScorekeeperAccount
        fields = ["username", "password", "games", "active"]

    def clean(self):
        cleaned = super().clean()
        if not self.instance.pk and not cleaned.get("password"):
            self.add_error("password", "Password is required for new scorekeepers.")
        return cleaned

    def save(self, commit=True):
        account = super().save(commit=False)
        raw_password = self.cleaned_data.get("password")
        if raw_password:
            account.set_password(raw_password)
        if commit:
            account.save()
            self.save_m2m()
        return account
