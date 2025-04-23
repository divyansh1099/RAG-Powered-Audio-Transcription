import argparse
import requests
from bs4 import BeautifulSoup
from tempfile import TemporaryDirectory
from fastapi import FastAPI
from fastapi.responses import JSONResponse
from langchain_openai import OpenAIEmbeddings, ChatOpenAI
from langchain_community.vectorstores import Chroma
from langchain.text_splitter import RecursiveCharacterTextSplitter
from langchain.docstore.document import Document
import urllib.parse
import logging

# === Configuration ===
MAX_CONTEXT_LENGTH = 3800
logger = logging.getLogger(__name__)

# === 1. Load and clean Wikipedia ===
def load_clean_wikipedia(topic: str) -> list[Document]:
    try:
        encoded_topic = urllib.parse.quote(topic.replace(' ', '_'))
        url = f"https://en.wikipedia.org/wiki/{encoded_topic}"
        response = requests.get(url, timeout=10)
        response.raise_for_status()
        html = response.text
        soup = BeautifulSoup(html, 'html.parser')
        content_div = soup.find('div', {'id': 'mw-content-text'})
        if not content_div:
            return [Document(page_content=f"No information found for {topic}", metadata={"source": url})]
        paragraphs = content_div.find_all('p')
        content = "\n\n".join([p.get_text() for p in paragraphs if p.get_text().strip()])
        if not content.strip():
            return [Document(page_content=f"No information found for {topic}", metadata={"source": url})]
        return [Document(page_content=content, metadata={"source": url})]
    except Exception as e:
        return [Document(page_content=f"Failed to retrieve information for {topic}: {str(e)}", metadata={"source": f"wikipedia/{topic}"})]

# === 2. Chunk text ===
def chunk_documents(documents: list[Document]) -> list[Document]:
    splitter = RecursiveCharacterTextSplitter(
        chunk_size=800, chunk_overlap=100,
        separators=["\n\n", "\n", ".", "!", "?"]
    )
    return splitter.split_documents(documents)

# === 3. Filter using LLM ===
def filter_chunks_with_llm(topic: str, docs: list[Document], llm=None) -> list[Document]:
    if not docs:
        return []
    if llm is None:
        llm = ChatOpenAI(model_name="gpt-3.5-turbo", temperature=0)
    batch_size = 5
    relevant_docs = []
    for i in range(0, len(docs), batch_size):
        batch = docs[i:i+batch_size]
        prompts = [
            f"Is the following text relevant to understanding or translating the topic?\n\n"
            f"Topic: {topic}\n"
            f"Text Chunk: {doc.page_content}\n\nRespond with 'Yes' or 'No' only."
            for doc in batch if doc.page_content
        ]
        responses = [llm.invoke(prompt).content.strip().lower() for prompt in prompts]
        for j, response in enumerate(responses):
            if j < len(batch) and "yes" in response:
                relevant_docs.append(batch[j])
    return relevant_docs or docs[:1]

# === 4. Main function ===
def get_filtered_rag_context(topic: str) -> str:
    raw_docs = load_clean_wikipedia(topic)
    if not raw_docs:
        return f"No information available for {topic}."
    split_docs = chunk_documents(raw_docs)
    if not split_docs:
        return f"No detailed information found for {topic}."
    embeddings = OpenAIEmbeddings()
    with TemporaryDirectory() as temp_dir:
        vector_db = Chroma.from_documents(split_docs, embeddings, persist_directory=temp_dir)
        retriever = vector_db.as_retriever(search_kwargs={"k": 8})
        top_docs = retriever.invoke(topic)
        if not top_docs:
            return f"No relevant information found for {topic}."
        filtered_docs = filter_chunks_with_llm(topic, top_docs)
        context = "\n\n".join(doc.page_content for doc in filtered_docs)
        return context[:MAX_CONTEXT_LENGTH]

# === 5. CLI ===
def cli():
    parser = argparse.ArgumentParser(description="Hybrid RAG: Retrieve clean context")
    parser.add_argument("--topic", required=True, help="The topic to search and extract context for")
    args = parser.parse_args()
    context = get_filtered_rag_context(args.topic)
    print("\n===== Filtered RAG Context =====\n")
    print(context)

# === 6. FastAPI route (optional) ===
app = FastAPI()

@app.get("/get_context")
def get_context(topic: str):
    try:
        context = get_filtered_rag_context(topic)
        return JSONResponse(content={"context": context})
    except Exception as e:
        return JSONResponse(content={"error": str(e)}, status_code=500)

# === 7. Entry point ===
if __name__ == "__main__":
    cli()