"""Front-end App - using streamlit for interactive usability"""

from good_start_habits.habits import (
    load_state,
    daily_maintenance,
    mark_done,
    state_init,
    check_current_datetime,
)
import streamlit as st
from good_start_habits.config import HABITS
from datetime import datetime


@st.fragment(run_every=1)  # reruns only this func every second
def clock():
    st.metric("Current Time", datetime.now().strftime("%H:%M:%S"))


clock()

st.title("good-start-habits")

if check_current_datetime():
    state_json = load_state()
    state_init(state_json)
    daily_maintenance(state_json)

    for habit in HABITS:
        if st.checkbox(habit):
            mark_done(state_json, habit)
else:
    st.write("🌙 Outside Active Hours 🌙")
