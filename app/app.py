import streamlit as st
import requests

API_BASE = "http://localhost:8000"

st.set_page_config(page_title="Audio Dubbing App", page_icon="🎙️", layout="centered")
st.title("🎙️ Audio Dubbing App")

st.markdown("""
    <style>
        /* Make all text inputs wider */
        input[type="text"], input[type="password"] {
            width: 100% !important;
            padding: 10px;
            font-size: 16px;
        }

        /* Center content */
        .block-container {
            max-width: 700px;
            margin: auto;
        }

        /* Customize buttons */
        button[kind="primary"] {
            background-color: #4CAF50;
            color: white;
        }

        /* Headings */
        h1 {
            text-align: center;
            color: #333;
        }
    </style>
""", unsafe_allow_html=True)

# Init session state
if "token" not in st.session_state:
    st.session_state.token = None
if "mode" not in st.session_state:
    st.session_state.mode = "Login"
if "email" not in st.session_state:
    st.session_state.email = ""
if "password" not in st.session_state:
    st.session_state.password = ""

# --------------------------------------------------
# 🟡 LAYOUT: LOGIN / REGISTER LANDING PAGE
# --------------------------------------------------
if not st.session_state.token:
    st.subheader("🔐 Please log in or register")

    st.radio("Mode", ["Login", "Register"], key="mode", horizontal=True)

    st.session_state.email = st.text_input("Email", value=st.session_state.email)
    st.session_state.password = st.text_input("Password", type="password", value=st.session_state.password)

    if st.button("Submit"):
        endpoint = "/auth/login" if st.session_state.mode == "Login" else "/auth/register"
        try:
            res = requests.post(API_BASE + endpoint, json={
                "email": st.session_state.email,
                "password": st.session_state.password
            })
            data = res.json()
            if res.status_code == 200:
                if "access_token" in data:
                    st.session_state.token = data["access_token"]
                    st.success("✅ Logged in successfully!")
                    st.rerun()
                else:
                    st.success("✅ Registered! Now switch to login.")
            else:
                st.error(f"❌ {data.get('detail', 'Error occurred')}")
        except Exception as e:
            st.error(f"❌ Request failed: {e}")

    st.stop()  # prevent the rest of the app from rendering
else:
    # --------------------------------------------------
    # ✅ LOGGED IN: Show Transcription & Dubbing App
    # --------------------------------------------------
    st.success("✅ Logged in")

    if st.button("Logout"):
        st.session_state.token = None
        st.rerun()

    st.subheader("🎧 Upload Audio for Transcription & Dubbing")
    uploaded_file = st.file_uploader("Upload audio file (.wav, .mp3, .m4a)", type=["wav", "mp3", "m4a"])

    if uploaded_file and st.button("Transcribe & Dub"):
        with st.spinner("Processing..."):
            try:
                files = {"file": (uploaded_file.name, uploaded_file.getvalue())}
                headers = {"Authorization": f"Bearer {st.session_state.token}"}
                res = requests.post(API_BASE + "/transcribe", files=files, headers=headers)

                if res.status_code == 200:
                    result = res.json()
                    st.success("✅ Done!")

                    st.markdown("### 📝 English Transcript")
                    st.write(result["transcript"])

                    st.markdown("### 🧠 Inferred Topic")
                    st.write(result["topic"])

                    st.markdown("### 📚 RAG Context")
                    st.info(result["rag_context_snippet"])

                    st.markdown("### 🗣️ Hindi Transcript")
                    st.write(result["hindi_transcript"])

                    st.markdown("### 🔊 Dubbed Audio")
                    st.audio(result["audio_output"], format="audio/mp3")
                else:
                    st.error(f"❌ Error {res.status_code}: {res.text}")
            except Exception as e:
                st.error(f"❌ Failed: {e}")
