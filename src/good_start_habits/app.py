"""Front-end App - created using streamlit for interactive usability"""

from good_start_habits.habits import load_state, daily_maintenance, mark_done
import streamlit as st

st.title("good-start-habits")
st.write("hello world")

state_json = load_state()
daily_maintenance(state_json)

if st.checkbox("SPF applied"):
    mark_done(state_json, "SPF applied")
if st.checkbox("Vitamins & Omega-3"):
    mark_done(state_json, "Vitamins & Omega-3")
if st.checkbox("Log meal"):
    mark_done(state_json, "Log meal")
if st.checkbox("Piano practice"):
    mark_done(state_json, "Piano practice")
if st.checkbox("Journal entry"):
    mark_done(state_json, "Journal entry")
if st.checkbox("Neuroscience notes"):
    mark_done(state_json, "Neuroscience notes")
if st.checkbox("Check to-do book"):
    mark_done(state_json, "Check to-do book")
if st.checkbox("Workout logged"):
    mark_done(state_json, "Workout logged")
if st.checkbox("Run logged"):
    mark_done(state_json, "Run logged")
