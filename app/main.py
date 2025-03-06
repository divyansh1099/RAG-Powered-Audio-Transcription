from fastapi import FastAPI, UploadFile, Form
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
import base64
from dotenv import load_dotenv
from . import transcription


load_dotenv()

app = FastAPI()

# Enable CORS for frontend communication
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Replace with specific Streamlit URL in production
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.post("/transcribe/")
async def transcribe_audio(
    file: UploadFile,
    language: str = Form(...),
    accent: str = Form(...)
):
    try:
        # Read and encode uploaded audio
        audio_data = await file.read()
        base64_audio = base64.b64encode(audio_data).decode('utf-8')

        # Transcribe audio
        english_transcription = transcription.transcribe_audio_to_text(base64_audio)

        # Prepare glossary (can be dynamic later)
        glossary = "Turbo, OpenAI, token, GPT, Dall-e, Python"

        # Dub audio
        hindi_result = transcription.dub_audio_to_hindi(base64_audio, glossary)

        response_data = {
            "transcription": hindi_result["hindi_transcript"],
            "audio_output": hindi_result["hindi_audio_base64"]
        }

        return JSONResponse(content=response_data)

    except Exception as e:
        return JSONResponse(
            status_code=500,
            content={"error": str(e)}
        )
