from io import BytesIO
from pydub import AudioSegment
from pydub.exceptions import CouldntDecodeError
from openai import OpenAI
import base64

client = OpenAI()

def transcribe_audio_with_whisper(audio_bytes):
    """
    Converts raw bytes to WAV and transcribes using Whisper.
    """
    try:
        audio = AudioSegment.from_file(BytesIO(audio_bytes))
        buffer = BytesIO()
        audio.export(buffer, format="wav")
        buffer.name = "audio.wav"
        buffer.seek(0)

        transcript = client.audio.transcriptions.create(
            model="whisper-1",
            file=buffer
        )
        return transcript.text

    except CouldntDecodeError:
        raise ValueError("❌ Could not decode audio file — invalid or unsupported format.")
    except Exception as e:
        raise ValueError(f"❌ Whisper transcription failed: {str(e)}")

def dub_audio_to_hindi(english_transcript, glossary, context_snippet=""):
    """
    Translates the transcript into Hindi with glossary support and generates TTS audio.
    """
    # Step 1: Translate using GPT-4o
    prompt = (
        f"You are a translation assistant. Use the following background context to improve the translation:\n\n"
        f"{context_snippet}\n\n"
        f"Translate the English transcript below to Hindi. Retain the following glossary terms in English: {glossary}.\n"
        f"Output must preserve the meaning and be suitable for spoken audio."
    )

    response = client.chat.completions.create(
        model="gpt-4o",
        messages=[
            {"role": "system", "content": prompt},
            {"role": "user", "content": english_transcript}
        ]
    )

    translated_text = response.choices[0].message.content

    # Step 2: Generate Hindi audio (mp3)
    audio_response = client.audio.speech.create(
        model="tts-1",
        voice="alloy",
        input=translated_text,
        response_format="mp3"
    )
    audio_data = audio_response.content
    audio_base64 = base64.b64encode(audio_data).decode("utf-8")

    return {
        "hindi_transcript": translated_text,
        "hindi_audio_base64": audio_base64
    }
