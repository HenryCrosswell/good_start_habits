# Tutorial: Getting started

By the end of this tutorial you will have the dashboard running locally, with habits displaying and the standby clock cycling correctly.

---

## What you need

- Python 3.12 or later
- `uv` installed (`pip install uv`)
- A terminal

---

## 1. Clone the repository

```bash
git clone <repo-url>
cd good_start_habits
```

---

## 2. Install dependencies

```bash
uv sync
```

This creates a virtual environment in `.venv/` and installs everything listed in `pyproject.toml`.

---

## 3. Create your `.env` file

The app needs at minimum a `SECRET_KEY` for Flask session signing.

```bash
cp .env.example .env
```

Open `.env` and set:

```
SECRET_KEY=<a long random string>
```

Generate one with:

```bash
python -c "import secrets; print(secrets.token_hex(32))"
```

The TrueLayer variables (`TRUELAYER_CLIENT_ID` etc.) are only needed if you want the budget page. You can leave them blank for now.

---

## 4. Run the app

```bash
flask --app src/good_start_habits/app.py run
```

Open `http://localhost:5000` in a browser.

---

## What you should see

- **Clock page** — the standby screen with the current time
- If the current time is within the active hours defined in `config.py`, the clock will automatically navigate to `/habits` after a few minutes and then return

---

## 5. Check your habits are showing

Navigate to `http://localhost:5000/habits`. You should see the habits scheduled for today (controlled by `HABIT_ACTIVE_DAYS` in `config.py`).

Click DONE on a habit. The streak increments. Click UNDO to reverse it.

---

## Next steps

- [Add or change a habit](../how-to/add-a-habit.md)
- [Connect a bank account](../how-to/connect-a-bank.md)
- [Deploy to Railway](../how-to/deploy-to-railway.md)
- [Set up as a Raspberry Pi kiosk](raspberry-pi-kiosk.md)
