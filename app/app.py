import streamlit as st
import requests
import base64
import time

# Streamlit app config
st.set_page_config(page_title="🎙️ RAG Audio Transcription", page_icon="🎧", layout="centered")

st.title("🎙️ RAG-Powered Audio Transcription with Domain Knowledge")
st.markdown("""
Upload an audio file, select your **language** and **accent**, and receive an enriched Hindi transcription with synthesized audio output.
""")

# Sidebar settings
with st.sidebar:
    st.header("⚙️ Settings")
    language = st.selectbox("Select Target Language", ["English", "Hindi"])
    accent = st.selectbox("Select Accent", ["Neutral", "Indian", "British"])

# Upload audio file
uploaded_file = st.file_uploader("🎤 Upload your audio file", type=["wav", "mp3", "m4a"])

MAX_RETRIES = 3  # Number of retries in case of backend failures


def transcribe_audio(file, language, accent):
    """
    Sends the uploaded audio, language, and accent to the FastAPI backend for processing.
    """
    form_data = {"language": language, "accent": accent}
    for attempt in range(MAX_RETRIES):
        try:
            response = requests.post(
                "http://localhost:8000/transcribe/",
                data=form_data,
                files={"file": file},
                timeout=120  # Timeout in seconds
            )
            if response.status_code == 200:
                return response.json()
            else:
                st.warning(f"Attempt {attempt + 1}: Received error {response.status_code}. Retrying...")
                time.sleep(2)
        except requests.exceptions.RequestException as e:
            st.warning(f"Attempt {attempt + 1}: Request failed ({e}). Retrying...")
            time.sleep(2)
    st.error("❌ Failed after multiple attempts. Please try again later.")
    return None


# Button to trigger processing
if uploaded_file and st.button("🚀 Transcribe and Generate Audio"):
    with st.spinner("Processing your audio... please wait."):
        result = transcribe_audio(uploaded_file, language, accent)

        if result:
            transcription = result["transcription"]
            audio_output = base64.b64decode(result["audio_output"])

            st.success("✅ Processing complete!")

            st.subheader("📝 Hindi Transcription")
            st.code(transcription, language="markdown")

            st.subheader("🔊 Synthesized Hindi Audio")
            st.audio(audio_output, format="audio/wav")

        else:
            st.error("Failed to process the audio. Please check the backend logs for more details.")
