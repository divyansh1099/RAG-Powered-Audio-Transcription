import os
import base64
import logging
import time
import requests
from io import BytesIO
from typing import List, Dict
from pydub import AudioSegment
from openai import OpenAI
from dotenv import load_dotenv

# Load environment variables
load_dotenv()
ASSEMBLYAI_API_KEY = os.getenv("ASSEMBLYAI_API_KEY")
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")

client = OpenAI(api_key=OPENAI_API_KEY)

logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)
logging.basicConfig(format='%(levelname)s:%(name)s:%(message)s')

AUDIO_CONVERT_FORMAT = "wav"
TTS_MODEL = "tts-1-hd"
voice_map = {
    "SPEAKER_0": "nova",
    "SPEAKER_1": "shimmer",
    "SPEAKER_2": "echo"
}

ASSEMBLY_HEADERS = { "authorization": ASSEMBLYAI_API_KEY }

def upload_audio_to_assemblyai(audio_bytes: bytes) -> str:
    response = requests.post(
        "https://api.assemblyai.com/v2/upload",
        headers=ASSEMBLY_HEADERS,
        data=audio_bytes
    )
    response.raise_for_status()
    return response.json()["upload_url"]

def transcribe_with_assemblyai(audio_bytes: bytes, input_lang: str = "en") -> List[Dict]:
    logger.info(f"📤 Uploading audio to AssemblyAI for input language: {input_lang}")
    upload_url = upload_audio_to_assemblyai(audio_bytes)

    payload = {
    "audio_url": upload_url,
    "speaker_labels": True,
    "language_code": input_lang  # NEW: specify transcription language
}

    response = requests.post(
        "https://api.assemblyai.com/v2/transcript",
        headers=ASSEMBLY_HEADERS,
        json=payload
    )
    response.raise_for_status()
    transcript_id = response.json()["id"]

    polling_endpoint = f"https://api.assemblyai.com/v2/transcript/{transcript_id}"
    logger.info("⏳ Waiting for transcription to complete...")
    while True:
        polling_response = requests.get(polling_endpoint, headers=ASSEMBLY_HEADERS)
        polling_data = polling_response.json()
        if polling_data["status"] == "completed":
            logger.info("✅ Transcription and diarization complete.")
            return polling_data.get("utterances", [])
        elif polling_data["status"] == "error":
            raise Exception(f"Transcription failed: {polling_data['error']}")
        time.sleep(5)

def translate_segments_with_gpt(target_lang: str, segments: List[Dict], context_snippet: str = "", glossary: str = "") -> List[Dict]:
    logger.info("🌐 Translating segments with GPT-4o...")
    
    # Defensive programming: ensure context is a string
    if context_snippet is None:
        context_snippet = ""
        logger.warning("⚠️ Received None context_snippet in translate_segments_with_gpt")
    
    translated = []
    for idx, seg in enumerate(segments):
        prompt = f"""**Role**: Expert Translator
**Task**: Translate the following English text to {target_lang.capitalize()}.
**Context**: {context_snippet}
**Glossary**: Preserve these English terms - {glossary}

**Text**:
{seg['text']}"""
        response = client.chat.completions.create(
            model="gpt-4o",
            messages=[
                {"role": "system", "content": "You are a professional translator."},
                {"role": "user", "content": prompt}
            ],
            temperature=0.3
        )
        translated_text = response.choices[0].message.content.strip()
        seg["translated_text"] = translated_text
        translated.append(seg)
        logger.info(f"📝 Translated segment {idx+1}/{len(segments)}")
    logger.info("✅ All segments translated.")
    return translated

def dub_translated_segments(translated_segments: List[Dict]) -> Dict:
    logger.info("🔊 Generating multi-voice dubbed audio...")
    final_audio = AudioSegment.empty()

    # Cycle of voices to assign dynamically
    voice_cycle = ["nova", "shimmer", "echo", "fable", "onyx"]

    # Create a speaker-to-voice map dynamically
    unique_speakers = list({seg["speaker"] for seg in translated_segments})
    speaker_voice_map = {speaker: voice_cycle[i % len(voice_cycle)] for i, speaker in enumerate(unique_speakers)}

    for idx, seg in enumerate(translated_segments):
        speaker = seg["speaker"]
        voice = speaker_voice_map.get(speaker, "nova")

        # TTS generation
        audio_response = client.audio.speech.create(
            model=TTS_MODEL,
            voice=voice,
            input=seg["translated_text"],
            response_format="mp3",
            speed=0.95
        )
        mp3_audio = BytesIO(audio_response.content)
        wav_chunk = AudioSegment.from_mp3(mp3_audio).set_frame_rate(44100)
        final_audio += wav_chunk

        logger.info(f"🔈 Dubbed segment {idx+1}/{len(translated_segments)} with voice: {voice} for speaker: {speaker}")

    # Encode full audio as base64 WAV
    with BytesIO() as buffer:
        final_audio.export(buffer, format=AUDIO_CONVERT_FORMAT)
        audio_base64 = base64.b64encode(buffer.getvalue()).decode("utf-8")

    logger.info("✅ Dubbing complete.")
    return {"dubbed_audio_base64": audio_base64}


def format_speaker_dubbing_response(translated_segments: List[Dict], audio_base64: str, input_lang: str, output_lang: str, topic: str = "TEMP_TOPIC", context_snippet: str = "TEMP_CONTEXT") -> Dict:
    logger.info("📦 Formatting final response...")

    return {
        "transcript": [
            {
                "speaker": seg["speaker"],
                "original_text": seg["text"],
                "translated_text": seg["translated_text"],
                "start": seg["start"],
                "end": seg["end"]
            }
            for seg in translated_segments
        ],
        f"{output_lang.lower()}_transcript": " ".join([seg["translated_text"] for seg in translated_segments]),
        "topic": topic,
        "rag_context_snippet": context_snippet,
        "audio_output": audio_base64  # just the base64 string, not the full data URI
    }


def full_assemblyai_transcription_pipeline(audio_bytes: bytes, input_lang: str, output_lang: str) -> List[Dict]:
    """
    Transcribes audio using AssemblyAI with the specified input language.
    Returns the raw transcribed segments without translation or dubbing.
    
    Args:
        audio_bytes: Binary audio data
        input_lang: Source language code (e.g., 'en', 'es')
        output_lang: Target language code (not used in this function but kept for API consistency)
        
    Returns:
        List of transcribed segments with speaker diarization
    """
    logger.info(f"🚀 Starting full pipeline: input_lang={input_lang}, output_lang={output_lang}")

    # Transcribe with input language
    segments = transcribe_with_assemblyai(audio_bytes, input_lang=input_lang)
    
    # Return just the segments without any further processing
    return segments

