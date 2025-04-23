import streamlit as st
import requests
from auth.session import init_session
init_session()

st.set_page_config(page_title="EchoVerse | Login", layout="centered")

# 🔐 Auto-redirect if already logged in
if "token" in st.session_state and st.session_state.token:
    st.switch_page("pages/1_dashboard.py")

st.markdown("## 🔐 Welcome to EchoVerse")
st.markdown("#### Login or Register to continue")

def clear_inputs():
    st.session_state.email = ""
    st.session_state.password = ""

auth_mode = st.radio(
    "Select mode", ["Login", "Register"],
    horizontal=True,
    key="auth_mode",
    on_change=clear_inputs
)

# Inputs
st.text_input("Email", key="email", placeholder="you@example.com")
st.text_input("Password", key="password", type="password", placeholder="Enter your password")

# Submit
if st.button("Submit", use_container_width=True):
    endpoint = "http://localhost:8000/auth/register" if auth_mode == "Register" else "http://localhost:8000/auth/login"
    response = requests.post(endpoint, json={
        "email": st.session_state.email,
        "password": st.session_state.password
    })

    if response.status_code == 200:
        data = response.json()
        if auth_mode == "Login" and "access_token" in data:
            st.session_state["token"] = data["access_token"]
            st.session_state["username"] = st.session_state.email.split("@")[0]  # or use actual username if backend returns it
            st.success("✅ Logged in successfully!")
            st.switch_page("pages/1_dashboard.py")
        elif auth_mode == "Register":
            st.success("✅ Registered successfully! Now switch to Login.")
    else:
        try:
            detail = response.json().get("detail", "Unknown error")
        except:
            detail = response.text
        st.error(f"Authentication failed: {detail}")
