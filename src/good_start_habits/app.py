"""Front-end App - using streamlit for interactive usability"""

from flask import Flask, render_template, redirect, url_for
from datetime import datetime
from good_start_habits.db import get_db, init_db
from good_start_habits.habits import (
    daily_maintenance,
    check_current_datetime,
    mark_done,
)
from good_start_habits.config import ROTATION_INTERVAL, DWELL_TIME

app = Flask(__name__)


@app.before_request
def fire_up_db():
    init_db()


@app.route("/")
def clock():
    if check_current_datetime():
        return render_template(
            "clock.html",
            active=True,
            rotation_interval=ROTATION_INTERVAL,
        )
    else:
        return render_template("clock.html", active=False)


@app.route("/habits")
def habits():
    db = get_db()
    daily_maintenance(db)
    habits = db.execute("SELECT name, streak, done_today FROM habits").fetchall()
    today = datetime.now().strftime("%A, %d %B %Y")
    return render_template(
        "habits.html", habits=habits, today=today, dwell_time=DWELL_TIME
    )


@app.route("/habits/<name>/done", methods=["POST"])
def habit_done(name: str):
    db = get_db()
    mark_done(db, name)
    return redirect(url_for("habits"))


@app.route("/habits/<name>/undo", methods=["POST"])
def habit_undo(name: str):
    db = get_db()
    mark_done(db, name, undo=True)
    return redirect(url_for("habits"))


@app.route("/budget")
def budget():
    return "<p>This my budget!</p>"


@app.route("/debug")
def debug():
    return render_template("debug.html")
