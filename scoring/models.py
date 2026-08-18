from django.contrib.auth.hashers import check_password, make_password
from django.core.exceptions import ValidationError
from django.db import models
from django.db.models.signals import post_delete, post_save
from django.dispatch import receiver
from django.utils.text import slugify


class EventCategory(models.TextChoices):
    TEAM = "team", "Team"
    INDIVIDUAL = "individual", "Individual"
    DOUBLES = "doubles", "Doubles"


class Team(models.Model):
    name = models.CharField(max_length=120, unique=True)
    colour = models.CharField(max_length=40, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["name"]

    def __str__(self):
        return self.name


class Player(models.Model):
    name = models.CharField(max_length=160)
    team = models.ForeignKey(Team, on_delete=models.SET_NULL, null=True, blank=True, related_name="players")
    shirt_size = models.CharField(max_length=20, blank=True)
    shirt_colour = models.CharField(max_length=40, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["name"]
        indexes = [models.Index(fields=["name"])]

    def __str__(self):
        return self.name


class Game(models.Model):
    name = models.CharField(max_length=160, unique=True)
    slug = models.SlugField(max_length=180, unique=True, blank=True)
    category = models.CharField(max_length=20, choices=EventCategory.choices)
    active = models.BooleanField(default=True)
    sort_order = models.PositiveIntegerField(default=0)
    scoring_notes = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["category", "sort_order", "name"]

    def save(self, *args, **kwargs):
        if not self.slug:
            base = slugify(self.name)[:170] or "game"
            slug = base
            suffix = 2
            while Game.objects.filter(slug=slug).exclude(pk=self.pk).exists():
                slug = f"{base}-{suffix}"[:180]
                suffix += 1
            self.slug = slug
        super().save(*args, **kwargs)

    def __str__(self):
        return self.name


class ScoreEntry(models.Model):
    game = models.ForeignKey(Game, on_delete=models.CASCADE, related_name="scores")
    team = models.ForeignKey(Team, on_delete=models.SET_NULL, null=True, blank=True, related_name="scores")
    player1 = models.ForeignKey(
        Player,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="primary_scores",
        verbose_name="Player",
    )
    player2 = models.ForeignKey(
        Player,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="partner_scores",
        verbose_name="Partner",
    )
    score = models.DecimalField(max_digits=9, decimal_places=2, default=0)
    rank = models.PositiveIntegerField(null=True, blank=True)
    notes = models.CharField(max_length=255, blank=True)
    recorded_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["game", "rank", "-score", "recorded_at"]
        verbose_name_plural = "score entries"

    @property
    def participant_label(self):
        if self.game.category == EventCategory.TEAM:
            return self.team.name if self.team else "Unassigned team"
        if self.game.category == EventCategory.DOUBLES:
            if self.player1_id or self.player2_id:
                first = self.player1.name if self.player1 else "Player 1"
                second = self.player2.name if self.player2 else "Player 2"
                return f"{first} / {second}"
            return self.team.name if self.team else "Unassigned team"
        return self.player1.name if self.player1 else self.team.name if self.team else "Unassigned team"

    def clean(self):
        if not self.game_id:
            return
        if not self.team_id:
            raise ValidationError("Scores need a team.")

    def __str__(self):
        return f"{self.game}: {self.participant_label}"


class ScorekeeperAccount(models.Model):
    username = models.CharField(max_length=80, unique=True)
    password_hash = models.CharField(max_length=128)
    games = models.ManyToManyField(Game, related_name="scorekeepers", blank=True)
    active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["username"]

    def set_password(self, raw_password):
        self.password_hash = make_password(raw_password)

    def check_password(self, raw_password):
        return check_password(raw_password, self.password_hash)

    def __str__(self):
        return self.username


def rank_game_scores(game_id):
    entries = list(ScoreEntry.objects.filter(game_id=game_id).order_by("-score", "recorded_at", "pk"))
    previous_score = None
    previous_rank = None
    changed = []

    for index, entry in enumerate(entries, start=1):
        rank = previous_rank if previous_score == entry.score else index
        if entry.rank != rank:
            entry.rank = rank
            changed.append(entry)
        previous_score = entry.score
        previous_rank = rank

    if changed:
        ScoreEntry.objects.bulk_update(changed, ["rank"])


@receiver(post_save, sender=ScoreEntry)
def update_score_ranks_after_save(sender, instance, raw=False, **kwargs):
    if not raw:
        rank_game_scores(instance.game_id)


@receiver(post_delete, sender=ScoreEntry)
def update_score_ranks_after_delete(sender, instance, **kwargs):
    rank_game_scores(instance.game_id)
