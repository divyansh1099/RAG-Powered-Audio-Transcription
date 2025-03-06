import requests
import os
import json
import base64
from dotenv import load_dotenv
from pydub import AudioSegment
from io import BytesIO

# Load environment variables from the .env file
load_dotenv()
API_KEY = os.getenv("OPENAI_API_KEY")
GPT_MODEL = os.getenv("GPT_MODEL", "gpt-4o-audio-preview")

# ---------- GPT-4o Audio Processing ----------

def process_audio_with_gpt_4o(base64_encoded_audio, output_modalities, system_prompt):
    """
    Sends an audio file (base64-encoded) to OpenAI's GPT-4o model for transcription or dubbing.
    
    Args:
        base64_encoded_audio (str): Base64 string of the audio file.
        output_modalities (list): Modalities required, e.g., ["text"], ["text", "audio"].
        system_prompt (str): Instruction for GPT-4o.

    Returns:
        dict: JSON response from the API if successful, otherwise None.
    """
    url = "https://api.openai.com/v1/chat/completions"

    headers = {
        "Content-Type": "application/json",
        "Authorization": f"Bearer {API_KEY}"
    }

    payload = {
        "model": GPT_MODEL,
        "modalities": output_modalities,
        "audio": {
            "voice": "alloy",
            "format": "wav"
        },
        "messages": [
            {"role": "system", "content": system_prompt},
            {
                "role": "user",
                "content": [
                    {
                        "type": "input_audio",
                        "input_audio": {
                            "data": base64_encoded_audio,
                            "format": "wav"
                        }
                    }
                ]
            }
        ]
    }

    response = requests.post(url, headers=headers, data=json.dumps(payload))
    
    if response.status_code == 200:
        return response.json()
    else:
        print(f"Error {response.status_code}: {response.text}")
        return None


# ---------- File Handling ----------

def load_audio_file_as_base64(file_path):
    """
    Reads an audio file and encodes it as a base64 string.

    Args:
        file_path (str): Path to the audio file.

    Returns:
        str: Base64 encoded string of the audio.
    """
    with open(file_path, "rb") as audio_file:
        return base64.b64encode(audio_file.read()).decode('utf-8')


# ---------- Transcription ----------

def transcribe_audio_to_text(base64_audio):
    """
    Transcribes audio to English text using GPT-4o.

    Args:
        base64_audio (str): Base64 string of the audio.

    Returns:
        str: Transcribed English text.
    """
    prompt = (
        "The user will provide an audio file in a certain language. "
        "Transcribe the audio to English text, word for word. "
        "Only provide the language transcription, do not include background noises such as applause."
    )
    modalities = ["text"]
    response = process_audio_with_gpt_4o(base64_audio, modalities, prompt)

    if response:
        return response['choices'][0]['message']['content']
    return None


# ---------- Dubbing ----------

def dub_audio_to_hindi(base64_audio, glossary):
    """
    Dubs English audio into Hindi while preserving specified glossary terms.

    Args:
        base64_audio (str): Base64 string of the audio.
        glossary (str): Comma-separated glossary of terms to keep in original language.

    Returns:
        dict: Dictionary containing Hindi transcript and base64 audio data.
    """
    prompt = (
        f"The user will provide an audio file in English. "
        f"Dub the complete audio, word for word in Hindi. "
        f"Keep certain words in English for which a direct translation in Hindi does not exist "
        f"such as {glossary}."
    )
    modalities = ["text", "audio"]
    response = process_audio_with_gpt_4o(base64_audio, modalities, prompt)

    if response:
        message = response['choices'][0]['message']
        return {
            "hindi_transcript": message['audio']['transcript'],
            "hindi_audio_base64": message['audio']['data']
        }
    return None


# ---------- Audio Playback (Optional for local testing) ----------

def play_audio_from_base64(audio_base64):
    """
    Plays an audio file from its base64 string.

    Args:
        audio_base64 (str): Base64 encoded audio data.
    """
    audio_bytes = base64.b64decode(audio_base64)
    audio_segment = AudioSegment.from_file(BytesIO(audio_bytes), format="wav")
    audio_segment.export("output.wav", format="wav")  # Optionally save the file
    # Uncomment below if running locally with playback support
    # from pydub.playback import play
    # play(audio_segment)


# ---------- Example Local Test ----------

if __name__ == "__main__":
    audio_file_path = "/Users/divyanshgupta/Downloads/FR_audio1.wav"
    glossary = "Turbo, OpenAI, token, GPT, Dall-e, Python"

    # Load audio
    base64_audio = load_audio_file_as_base64(audio_file_path)

    # Transcribe
    english_transcript = transcribe_audio_to_text(base64_audio)
    print("\nEnglish Transcript:\n", english_transcript)

    # Dub to Hindi
    hindi_result = dub_audio_to_hindi(base64_audio, glossary)
    if hindi_result:
        print("\nHindi Transcript:\n", hindi_result["hindi_transcript"])
        play_audio_from_base64(hindi_result["hindi_audio_base64"])
