import streamlit as st
import requests
import base64

API_BASE = "http://localhost:8000"

st.set_page_config(page_title="Audio Dubbing App", page_icon="🎙️", layout="centered")
st.title("🎙️ Audio Dubbing App")

# 🛡️ Require Login
if "token" not in st.session_state or not st.session_state.token:
    st.error("🔐 Please login from the Home page first.")
    st.stop()

# 🔓 Logout option (sidebar only after login)
with st.sidebar:
    st.success(f"👋 Logged in as: {st.session_state.get('email', 'User')}")
    if st.button("Logout"):
        st.session_state.token = None
        st.session_state.email = ""
        st.session_state.password = ""
        st.rerun()

# 🌐 Language selection
st.subheader("🌍 Select Target Language")
target_language = st.selectbox("Choose language for dubbing", ["Hindi", "French", "Spanish"], index=0)

# 🎧 Upload + Transcription
st.subheader("🎧 Upload Audio for Transcription & Dubbing")
uploaded_file = st.file_uploader("Upload audio file (.wav, .mp3, .m4a)", type=["wav", "mp3", "m4a"])

if uploaded_file and st.button("Transcribe & Dub"):
    with st.spinner("Processing..."):
        try:
            files = {"file": (uploaded_file.name, uploaded_file.getvalue())}
            headers = {
                "Authorization": f"Bearer {st.session_state.token}",
            }
            data = {
                "username": st.session_state["username"],
                "target_lang": target_language.lower(),
                "glossary": "OpenAI, GPT, token"
            }

            res = requests.post(f"{API_BASE}/transcribe", files=files, headers=headers, data=data)

            if res.status_code == 200:
                result = res.json()
                st.markdown("### 📝 English → Translated Transcript")

                transcript_data = result.get("transcript", [])
                if isinstance(transcript_data, list):
                    # Build a single formatted string block
                    transcript_html = ""
                    for seg in transcript_data:
                        speaker = seg.get("speaker", "Unknown")
                        original = seg.get("original_text", "").strip()
                        translated = seg.get("translated_text", "").strip()

                        block = f"""
            <div style='margin-bottom: 1.5rem;'>
                <strong>🎙️ Speaker {speaker}</strong><br>
                <span style='display: block; margin-top: 0.5rem;'>
                    🟦 <strong>Original:</strong><br> {original}
                </span>
                <span style='display: block; margin-top: 0.5rem;'>
                    🟩 <strong>Translated:</strong><br> {translated}
                </span>
            </div>
            <hr style='border: 0.5px solid #ddd;'>
            """
                        transcript_html += block

                    # Display inside a scrollable box
                    st.markdown(
                        f"""
            <div style='max-height: 400px; overflow-y: auto; padding: 1rem; border: 1px solid #ccc; border-radius: 10px; background-color: #1e1e1e; color: #f1f1f1;'>
                {transcript_html}
            </div>
            """,
                        unsafe_allow_html=True
                    )
                else:
                    st.warning("Transcript format unexpected.")

                st.markdown("### 🔊 Dubbed Audio")
                audio_output = base64.b64decode(result["audio_output"])
                st.audio(audio_output, format="audio/wav")

                b64_audio = result["audio_output"]
                href = f'<a href="data:audio/wav;base64,{b64_audio}" download="dubbed_audio.wav">📥 Download Dubbed Audio</a>'
                st.markdown(href, unsafe_allow_html=True)

            else:
                st.error(f"❌ Error {res.status_code}: {res.text}")
        except Exception as e:
            st.error(f"❌ Failed: {e}")
