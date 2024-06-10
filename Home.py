import streamlit as st
from menu import menu
from login import log_in, register_user, forgot_password, forgot_username, load_users

st.set_page_config(page_title="Home", page_icon="🏠", layout="wide")

# Initialize st.session_state.role to None
if "authentication_status" not in st.session_state:
    st.session_state.authentication_status = None


# Retrieve the role from Session State to initialize the widget
st.session_state._authentication_status = st.session_state.authentication_status

menu()
    

st.write("# Welcome to Streamline Data Manager")

# Loading credentials file and start log in
load_users()
log_in()

if st.session_state.authentication_status is not True:
    if st.button("Register"):
        register_user()
    if st.button("Reset Password"):
        forgot_password()
    if st.button("Reset username"):
        forgot_username()



