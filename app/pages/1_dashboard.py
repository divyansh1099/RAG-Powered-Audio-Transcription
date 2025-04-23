import streamlit as st
import pymongo
import pandas as pd
import base64
from datetime import datetime

# --- Setup
st.set_page_config(page_title="EchoVerse | Dashboard", layout="wide")

if "token" not in st.session_state or "username" not in st.session_state:
    st.error("Unauthorized. Please log in from the homepage.")
    st.stop()

st.sidebar.success(f"👋 Logged in as: {st.session_state['username']}")

# --- Connect to MongoDB
client = pymongo.MongoClient("mongodb://localhost:27017")
db = client["dubbGPT"]
collection = db["transcripts"]

user_uploads = list(collection.find({"username": st.session_state["username"]}))
if not user_uploads:
    st.warning("You haven't uploaded any audio yet.")
    st.stop()

# --- Convert to DataFrame
df = pd.DataFrame(user_uploads)
df["Date"] = df["timestamp"].apply(lambda t: datetime.fromtimestamp(t).strftime("%Y-%m-%d %H:%M"))

# --- Filters
topics = df["topic"].dropna().unique().tolist()
langs = df["target_lang"].dropna().unique().tolist()

with st.sidebar:
    st.markdown("### 📂 Filters")
    topic_filter = st.multiselect("Filter by topic", topics)
    lang_filter = st.multiselect("Filter by language", langs)

# --- Apply Filters
if topic_filter:
    df = df[df["topic"].isin(topic_filter)]
if lang_filter:
    df = df[df["target_lang"].isin(lang_filter)]

# --- Layout
st.title("📊 Your Upload Dashboard")
st.markdown("Use filters on the left. View, play, and download your audio & transcripts below.")


for idx, row in df.iterrows():
    st.markdown("---")
    cols = st.columns([1.5, 1.2, 0.8, 1.5, 2, 0.7])

    with cols[0]:
        st.markdown(f"📌 **{row['topic']}**")

    with cols[1]:
        st.markdown(f"📅 {row['Date']}")

    with cols[2]:
        st.markdown(f"🌐 `{row['target_lang']}`")

    with cols[3]:
        transcript = row.get("translated_transcript", "")
        if not isinstance(transcript, str):
            transcript = ""

        txt_data = transcript.encode("utf-8")
        st.download_button("📄 TXT", txt_data, file_name=f"{row['topic']}.txt", key=f"txt_{idx}")

    with cols[4]:
        audio_id = str(row.get("audio_id", ""))
        if audio_id:
            st.audio(f"http://localhost:8000/audio/{audio_id}", format="audio/wav")
        else:
            st.warning("⚠️ Audio ID not found.")

    with cols[5]:
        if audio_id:
            st.markdown(
                f'[📥 Download Audio](http://localhost:8000/audio/download/{audio_id})',
                unsafe_allow_html=True
            )