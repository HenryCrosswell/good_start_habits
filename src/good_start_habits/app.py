"""Front-end App - created using streamlit for interactive usability"""

from good_start_habits.habits import (
    load_state,
    daily_maintenance,
    mark_done,
    state_init,
)
import streamlit as st
from good_start_habits.config import HABITS

st.title("good-start-habits")
st.write("hello world")


state_json = load_state()
state_init(state_json)
daily_maintenance(state_json)

for habit in HABITS:
    if st.checkbox(habit):
        mark_done(state_json, habit)
