from django.urls import path

from . import views


app_name = "scoring"

urlpatterns = [
    path("", views.home, name="home"),
    path("players/<int:pk>/", views.player_detail, name="player_detail"),
    path("teams/<int:pk>/", views.team_detail, name="team_detail"),
    path("scorekeeper/login/", views.scorekeeper_login, name="scorekeeper_login"),
    path("scorekeeper/logout/", views.scorekeeper_logout, name="scorekeeper_logout"),
    path("scorekeeper/", views.scorekeeper_dashboard, name="scorekeeper_dashboard"),
    path("scorekeeper/games/<slug:slug>/", views.scorekeeper_game, name="scorekeeper_game"),
]
