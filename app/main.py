from fastapi import FastAPI, UploadFile, HTTPException, File, Form
from fastapi.middleware.cors import CORSMiddleware
from app.transcription import (
    full_assemblyai_transcription_pipeline,
    translate_segments_with_gpt,
    dub_translated_segments,
    format_speaker_dubbing_response
)
from app.auth.routes import router as auth_router
from app.rag_hybrid import get_filtered_rag_context
from openai import OpenAI
import os
import uuid
import logging
import asyncio
import time
from pymongo import MongoClient
from concurrent.futures import ThreadPoolExecutor

app = FastAPI()
logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# MongoDB setup 
client = MongoClient("mongodb://localhost:27017")
db = client["dubbGPT"]
collection = db["transcripts"]

# Include auth
app.include_router(auth_router, prefix="/auth", tags=["Auth"])

@app.post("/transcribe", tags=["Transcription"])
async def process_multispeaker_audio(
    file: UploadFile = File(...),
    username: str = Form(...),
    glossary: str = "OpenAI, GPT, token, Python",
    target_lang: str = "hindi"
):
    try:
        file_bytes = await file.read()
        if len(file_bytes) < 1000:
            raise ValueError("❌ Uploaded file is too small or empty.")
        
        logger.info(f"📦 File size: {len(file_bytes) / (1024 * 1024):.2f} MB")

        with ThreadPoolExecutor() as executor:
            loop = asyncio.get_event_loop()

            temp_filename = f"/tmp/{uuid.uuid4().hex}_{file.filename}"
            with open(temp_filename, "wb") as f:
                f.write(file_bytes)

            try:
                # Transcription & diarization
                segments = await loop.run_in_executor(
                    executor, full_assemblyai_transcription_pipeline, file_bytes
                )

                full_transcript = " ".join([seg["text"] for seg in segments])

                # Topic inference
                client = OpenAI()
                topic = await loop.run_in_executor(
                    executor,
                    lambda: client.chat.completions.create(
                        model="gpt-4o",
                        messages=[
                            {"role": "system", "content": "Summarize the main topic of the transcript strictly in not more than 2 words."},
                            {"role": "user", "content": full_transcript}
                        ]
                    ).choices[0].message.content.strip()
                )
                logger.info(f"🔍 Inferred topic: {topic}")

                # RAG context (wrapped in fallback)
                try:
                    context_snippet = await loop.run_in_executor(
                        executor, get_filtered_rag_context, topic
                    )
                except Exception as e:
                    logger.warning(f"⚠️ RAG failed, using fallback context: {e}")
                    context_snippet = f"Fallback context for topic: {topic}"

                # Translation
                translated_segments = await loop.run_in_executor(
                    executor,
                    lambda: translate_segments_with_gpt(
                        segments,
                        context_snippet=context_snippet,
                        glossary=glossary,
                        target_lang=target_lang
                    )
                )

                # Dubbing
                audio_output = await loop.run_in_executor(
                    executor, dub_translated_segments, translated_segments
                )

                # Response formatting
                response = format_speaker_dubbing_response(
                    translated_segments,
                    audio_output["hindi_audio_base64"]
                ) 

                hindi_transcript = " ".join([seg["translated_text"] for seg in translated_segments])


                # Insert into MongoDB
                collection.insert_one({
                    "username": username,
                    "timestamp": time.time(),
                    "topic": topic,
                    "target_lang": target_lang,
                    "transcript": full_transcript,
                    "translated_transcript": hindi_transcript,
                    "dubbed_audio_b64": audio_output["hindi_audio_base64"]
                })
                return response

            finally:
                if os.path.exists(temp_filename):
                    os.remove(temp_filename)

    except Exception as e:
        logger.error(f"❌ Error in multi-speaker route: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))
