"""Front-end App - using streamlit for interactive usability"""

from flask import Flask, render_template, redirect, url_for
from datetime import datetime
from good_start_habits.db import get_db, init_db
from good_start_habits.habits import (
    daily_maintenance,
    check_current_datetime,
    mark_done,
)

app = Flask(__name__)


@app.before_request
def fire_up_db():
    init_db()


@app.route("/")
def clock():
    if check_current_datetime():
        active = "*"
        return render_template(
            "clock.html", clock=datetime.now().strftime("%H:%M:%S"), active=active
        )
        # and functionality to switch to habits and budget
    else:
        return render_template("clock.html", clock=datetime.now().strftime("%H:%M:%S"))


@app.route("/habits")
def habits():
    db = get_db()
    daily_maintenance(db)
    habits = db.execute("SELECT name, streak, done_today FROM habits").fetchall()
    return render_template("habits.html", habits=habits)


@app.route("/habits/<name>/done", methods=["POST"])
def habit_done(name: str):
    db = get_db()
    mark_done(db, name)
    return redirect(url_for("habits"))


@app.route("/budget")
def budget():
    return "<p>This my budget!</p>"


# @st.fragment(run_every=1)  # reruns only this func every second
# def clock():
#     st.metric(

# clock()

# st.title("good-start-habits")

# if check_current_datetime():
#     state_json = load_state()
#     state_init(state_json)
#     daily_maintenance(state_json)

#     for habit in HABITS:
#         if st.checkbox(habit):
#             mark_done(state_json, habit)
# else:
#     st.write("🌙 Outside Active Hours 🌙")
