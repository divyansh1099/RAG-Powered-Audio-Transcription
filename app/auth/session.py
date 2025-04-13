import streamlit as st

DEFAULT_SESSION_KEYS = {
    "token": None,
    "email": None,
    "auth_mode": "Login",
    "password": "",
}

def init_session():
    for key, default in DEFAULT_SESSION_KEYS.items():
        if key not in st.session_state:
            st.session_state[key] = default

def logout():
    for key in DEFAULT_SESSION_KEYS:
        if key in st.session_state:
            del st.session_state[key]
