import streamlit as st
import pymongo
import pandas as pd
import base64
from datetime import datetime

# --- Setup
st.set_page_config(page_title="DubbGPT | Dashboard", layout="wide")

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
        txt_data = row.get("translated_transcript", "").encode("utf-8")
        srt_data = f"1\n00:00:00,000 --> 00:00:20,000\n{row.get('translated_transcript', '')}\n".encode("utf-8")
        st.download_button("📄 TXT", txt_data, file_name=f"{row['topic']}.txt", key=f"txt_{idx}")
        st.download_button("🎞 SRT", srt_data, file_name=f"{row['topic']}.srt", key=f"srt_{idx}")

    with cols[4]:
        try:
            audio_data = base64.b64decode(row["dubbed_audio_b64"])
            st.audio(audio_data, format="audio/mp3")
        except Exception as e:
            st.warning("⚠️ Audio missing")

    with cols[5]:
        if "dubbed_audio_b64" in row:
            b64 = base64.b64encode(audio_data).decode()
            st.markdown(
                f'<a href="data:audio/mp3;base64,{b64}" download="dubbed_audio.mp3">📥</a>',
                unsafe_allow_html=True
            )