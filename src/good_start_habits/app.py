"""Front-end App - created using streamlit for interactive usability"""

import streamlit as st


st.title("good-start-habits")
st.write("hello world")

"""
Checkboxes to show completion of tasks

Ticking will stop any escalation alarm
"""


if st.checkbox("SPF applied"):
    st.write("Good Job!")
if st.checkbox("Vitamins & Omega-3"):
    st.write("Good Job!")
if st.checkbox("Log meal"):
    st.write("On MFP? Nice!")
st.checkbox("Piano practice")
st.checkbox("Journal entry")
st.checkbox("Neuroscience notes")
st.checkbox("Check to-do book")
st.checkbox("Workout logged")
st.checkbox("Run logged")
