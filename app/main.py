from fastapi import FastAPI, HTTPException, UploadFile
from fastapi.middleware.cors import CORSMiddleware
from .transcription import transcribe_audio_with_whisper, dub_audio_to_hindi
from langchain_community.vectorstores import Chroma
from langchain_openai import OpenAIEmbeddings
from langchain_core.documents import Document
from langchain_community.document_loaders import WebBaseLoader
from langchain_text_splitters import RecursiveCharacterTextSplitter
from tempfile import TemporaryDirectory
from openai import OpenAI

app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.post("/transcribe/")
async def process_audio(file: UploadFile):
    try:
        file_bytes = await file.read()
        if len(file_bytes) < 1000:
            raise ValueError("❌ Uploaded file is too small or empty.")

        english_transcript = transcribe_audio_with_whisper(file_bytes)
        if not english_transcript:
            raise HTTPException(status_code=500, detail="Transcription failed.")

        # Identify topic
        client = OpenAI()
        topic_response = client.chat.completions.create(
            model="gpt-4o",
            messages=[
                {"role": "system", "content": "Summarize the main topic of the transcript in 3-5 words."},
                {"role": "user", "content": english_transcript}
            ]
        )
        topic = topic_response.choices[0].message.content.strip()
        print("🔍 Inferred Topic:", topic)

        # Load content from the web
        search_urls = [f"https://en.wikipedia.org/wiki/{topic.replace(' ', '_')}"]
        loader = WebBaseLoader(search_urls)
        web_docs = loader.load()

        # Split and embed
        splitter = RecursiveCharacterTextSplitter(chunk_size=1000, chunk_overlap=200)
        split_docs = splitter.split_documents(web_docs)
        embeddings = OpenAIEmbeddings()
        temp_dir = TemporaryDirectory()
        vector_db = Chroma.from_documents(split_docs, embeddings, persist_directory=temp_dir.name)

        # RAG retrieval
        retriever = vector_db.as_retriever(search_kwargs={"k": 1})
        rag_context = retriever.invoke("What is this audio about?")
        context_snippet = rag_context[0].page_content if rag_context else ""

        # Dubbing with context
        glossary = "OpenAI, GPT, token, Python"
        dubbing_result = dub_audio_to_hindi(english_transcript, glossary, context_snippet)

        return {
            "transcript": english_transcript,
            "rag_context_snippet": context_snippet,
            "topic": topic,
            "hindi_transcript": dubbing_result["hindi_transcript"],
            "audio_output": dubbing_result["hindi_audio_base64"]
        }

    except Exception as e:
        print("❌ Error:", str(e))
        raise HTTPException(status_code=500, detail=str(e))
