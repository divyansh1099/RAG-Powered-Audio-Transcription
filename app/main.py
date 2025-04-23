import argparse
import requests
from bs4 import BeautifulSoup
from tempfile import TemporaryDirectory
from fastapi import FastAPI, UploadFile, HTTPException, File, Form
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from langchain_openai import OpenAIEmbeddings, ChatOpenAI
from langchain_community.vectorstores import Chroma
from langchain.text_splitter import RecursiveCharacterTextSplitter
from langchain.docstore.document import Document
from app.transcription import (
    full_assemblyai_transcription_pipeline,
    translate_segments_with_gpt,
    dub_translated_segments,
    format_speaker_dubbing_response
)
from app.auth.routes import router as auth_router
from app.rag_hybrid import get_filtered_rag_context
from openai import OpenAI
from pymongo import MongoClient
from gridfs import GridFS
import os
import uuid
import logging
import asyncio
import base64
import time
from concurrent.futures import ThreadPoolExecutor
import urllib.parse

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
fs = GridFS(db)

# Include auth
app.include_router(auth_router, prefix="/auth", tags=["Auth"])

@app.post("/transcribe", tags=["Transcription"])
async def process_multispeaker_audio(
    file: UploadFile = File(...),
    username: str = Form(...),
    input_lang: str = Form(...),
    target_lang: str = Form(...),
    glossary: str = Form("OpenAI, GPT, token, Python")
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
                segments = await loop.run_in_executor(
                    executor,
                    lambda: full_assemblyai_transcription_pipeline(
                        file_bytes, input_lang=input_lang, output_lang=target_lang)
                )
                full_transcript = " ".join([seg["text"] for seg in segments])

                openai_client = OpenAI()
                topic = await loop.run_in_executor(
                    executor,
                    lambda: openai_client.chat.completions.create(
                        model="gpt-4o",
                        messages=[
                            {"role": "system", "content": "You are an entity extractor. From the transcript below, identify the primary subject (person, place, or proper noun) being discussed. Reply in no more than two words and include only that entity’s name."},
                            {"role": "user", "content": full_transcript}
                        ]
                    ).choices[0].message.content.strip()
                )

                try:
                    context_snippet = await loop.run_in_executor(
                        executor, get_filtered_rag_context, topic
                    )
                    if context_snippet is None or not isinstance(context_snippet, str):
                        context_snippet = f"Fallback context for topic: {topic}"
                except Exception as e:
                    context_snippet = f"Fallback context for topic: {topic}"

                translated_segments = await loop.run_in_executor(
                    executor,
                    lambda: translate_segments_with_gpt(
                        target_lang=target_lang,
                        segments=segments,
                        context_snippet=context_snippet,
                        glossary=glossary
                    )
                )

                translated_transcript = " ".join([seg["translated_text"] for seg in translated_segments])

                audio_output = await loop.run_in_executor(
                    executor, dub_translated_segments, translated_segments
                )

                # Save audio to GridFS
                audio_binary = base64.b64decode(audio_output["dubbed_audio_base64"])
                audio_id = fs.put(audio_binary, filename=f"{username}_{uuid.uuid4().hex}.wav")

                response = format_speaker_dubbing_response(
                    translated_segments=translated_segments,
                    audio_base64=audio_output["dubbed_audio_base64"],
                    input_lang=input_lang,
                    output_lang=target_lang,
                    topic=topic,
                    context_snippet=context_snippet
                )

                collection.insert_one({
                    "username": username,
                    "timestamp": time.time(),
                    "topic": topic,
                    "target_lang": target_lang,
                    "transcript": full_transcript,
                    "translated_transcript": translated_transcript,
                    "audio_id": audio_id
                })

                return response

            finally:
                if os.path.exists(temp_filename):
                    os.remove(temp_filename)

    except Exception as e:
        logger.error(f"❌ Error in multi-speaker route: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))
