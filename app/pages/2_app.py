import streamlit as st
import requests
import base64
from streamlit_lottie import st_lottie

API_BASE = "http://localhost:8000"

def load_lottie_url(url):
    response = requests.get(url)
    if response.status_code != 200:
        return None
    return response.json()

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
language_map = {
    "Global English": "en",
    "British English": "en_uk",
    "US English": "en_us",
    "Hindi": "hi",
    "Spanish": "es",
    "French": "fr",
    "German": "de",
    "Chinese": "zh",
    "Japanese": "ja",
    "Korean": "ko",
    "Russian": "ru",
    "Portuguese": "pt",
    "Italian": "it"
}

st.subheader("🌍 Language Selection")
input_display = st.selectbox("Input Language", list(language_map.keys()), index=0)
target_display = st.selectbox("Output (Dubbing) Language", list(language_map.keys()), index=3)

input_lang = language_map[input_display]
target_lang = language_map[target_display]

# 🎧 Upload + Transcription
st.subheader("🎧 Upload Audio for Transcription & Dubbing")
uploaded_file = st.file_uploader("Upload audio file (.wav, .mp3, .m4a)", type=["wav", "mp3", "m4a"])

if uploaded_file:
    if input_lang == target_lang:
        st.warning("⚠️ Input and output languages must be different.")
    elif st.button("Transcribe & Dub"):
        lottie_url = "https://assets4.lottiefiles.com/packages/lf20_yej6quuc.json"  # Replace if desired
        lottie_processing = load_lottie_url(lottie_url)
        st.markdown("#### 🎬 Sit tight while we dub your audio...")

        with st.spinner("🧠 Translating and generating dubbed audio... This may take up to a minute."):
            if lottie_processing:
                st_lottie(lottie_processing, height=200, key="dubbing_lottie")

            try:
                files = {"file": (uploaded_file.name, uploaded_file.getvalue())}
                headers = {
                    "Authorization": f"Bearer {st.session_state.token}",
                }
                data = {
                    "username": st.session_state["username"],
                    "input_lang": input_lang,
                    "target_lang": target_lang,
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
