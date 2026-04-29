# good-start-habits

A personal dashboard that lives in a browser tab or on a Raspberry Pi screen. It shows your habits, budget, and a standby clock. During active hours the screen cycles between the clock and your habit checklist — no notifications, no nagging, just a passive glance when the display changes.

Built with Flask, SQLite, and Plotly. No external CSS frameworks, no JavaScript build step.

---

## Deployment options

| Target | Method | Notes |
|---|---|---|
| Local development | `flask run` | Dev server, hot reload |
| Railway (cloud) | Docker via `railway up` | Production Gunicorn server |
| Raspberry Pi (kiosk) | Docker Compose | Full kiosk mode via Chromium |

---

## Quick start (local)

```bash
uv sync
cp .env.example .env   # fill in SECRET_KEY at minimum
flask --app src/good_start_habits/app.py run
```

The app will be at `http://localhost:5000`. The database (`dashboard.db`) is created automatically on first run.

---

## Quick start (Docker / Pi)

```bash
cp .env.example .env   # fill in all values
touch dashboard.db     # create the file before mounting
docker compose up -d
```

The app will be at `http://localhost:5000`.

---

## Documentation

Full documentation is in [`docs/`](docs/). The structure follows the [Diataxis](https://diataxis.fr) framework:

| Section | What's in it |
|---|---|
| [Tutorials](docs/tutorials/) | Step-by-step walkthroughs — first run, Pi kiosk setup |
| [How-to guides](docs/how-to/) | Task-focused recipes — add a habit, connect a bank, deploy |
| [Reference](docs/reference/) | Complete technical reference — config, routes, database |
| [Explanation](docs/explanation/) | Concepts — how streaks work, how categorisation works |

---

## Running tests

```bash
pytest
pytest -v
pytest --cov=src
```

Tests use in-memory SQLite and make no network calls.

---

## Linting and type-checking

```bash
ruff check .
ruff format .
mypy src/
```
