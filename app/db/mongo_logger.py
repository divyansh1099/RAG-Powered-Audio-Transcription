from pymongo import MongoClient
from datetime import datetime
import base64

# Setup MongoDB connection
client = MongoClient("mongodb://localhost:27017")
db = client["dubbGPT"]
collection = db["transcripts"]

def log_transcription_output(username, topic, english_transcript, translated_text, audio_bytes, filename="audio", target_lang="hindi"):
    """
    Save a transcription + dubbing result into MongoDB.
    """
    audio_base64 = base64.b64encode(audio_bytes).decode("utf-8")

    document = {
        "username": username,
        "filename": filename,
        "topic": topic,
        "transcript": english_transcript,
        "translated_transcript": translated_text,
        "dubbed_audio_b64": audio_base64,
        "target_lang": target_lang,
        "timestamp": datetime.now().timestamp()
    }

    collection.insert_one(document)
