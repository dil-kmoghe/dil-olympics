# Office Olympics Scoring

Django app for Office Olympics team, individual, and doubles scoring.

## Run Locally

```bash
source .venv/bin/activate
python manage.py runserver
```

Open:

- Public scoreboard/search: http://127.0.0.1:8000/
- Scorekeeper login: http://127.0.0.1:8000/scorekeeper/login/
- Full admin: http://127.0.0.1:8000/admin/

## Run With Docker For LAN Access

```bash
docker-compose up -d --build
```

The app listens on `0.0.0.0:8000`, so people on the same network can open:

```text
http://YOUR_MACHINE_IP:8000/
```

Stop it with:

```bash
docker-compose down
```

## Run With Docker

```bash
docker compose up --build -d
```

Open http://127.0.0.1:8000/.

For a real server, set these environment variables before starting:

```bash
export DJANGO_SECRET_KEY="replace-with-a-long-random-secret"
export DJANGO_ALLOWED_HOSTS="your-domain.com,www.your-domain.com"
export DJANGO_CSRF_TRUSTED_ORIGINS="https://your-domain.com,https://www.your-domain.com"
docker compose up --build -d
```

The Compose setup stores SQLite data in the `olympics_data` Docker volume.

## Seed Data

The current SQLite database is already seeded from:

```text
/Users/kmoghe/Downloads/Office_Olympics_Team_and_Tshirt_Lists.xlsx
```

To rebuild from scratch:

```bash
python manage.py migrate
python manage.py seed_olympics --excel /Users/kmoghe/Downloads/Office_Olympics_Team_and_Tshirt_Lists.xlsx --create-admin --create-scorekeepers
```

The seed command preloads all games, imports players and teams from the workbook, and can create one scorekeeper account per game.

## Local Admin

Default local admin created by the seed command:

```text
username: admin
password: admin123
```

Change this before sharing the app outside your machine.

## Admin Workflow

Use `/admin/` to add, edit, or remove:

- Teams
- Players
- Games
- Score entries
- Scorekeeper accounts

For game-specific scoring access, create or edit a `Scorekeeper account`, set a password, and assign the games that account can score.

Scorekeepers enter scores by selecting a team. Rankings are recalculated automatically for each game from highest score to lowest score, with tied scores sharing the same rank.
