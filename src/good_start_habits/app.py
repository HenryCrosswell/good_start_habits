"""Front-end App - using streamlit for interactive usability"""

from flask import Flask

app = Flask(__name__)


@app.route("/")
def hello_world():
    return "<p>Hello, World!</p>"


@app.route("/clock")
def clock():
    return "<p>This my clock!</p>"


@app.route("/habits")
def habits():
    return "<p>These my habits!</p>"


@app.route("/budget")
def budget():
    return "<p>This my budget!</p>"


# @st.fragment(run_every=1)  # reruns only this func every second
# def clock():
#     st.metric("Current Time", datetime.now().strftime("%H:%M:%S"))


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
