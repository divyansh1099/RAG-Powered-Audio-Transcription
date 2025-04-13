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
import time
from tenacity import retry, stop_after_attempt, wait_exponential


# === 1. Load and clean Wikipedia ===
@retry(stop=stop_after_attempt(3), wait=wait_exponential(multiplier=1, min=4, max=10))
def load_clean_wikipedia(topic: str) -> list[Document]:
    # Existing implementation with error handling
    try:
        url = f"https://en.wikipedia.org/wiki/{topic.replace(' ', '_')}"
        response = requests.get(url, timeout=10)
        response.raise_for_status()  # Raise exception for 4XX/5XX responses
        html = response.text
        # Rest of implementation
    except requests.exceptions.RequestException as e:
        logger.error(f"Error fetching Wikipedia content: {e}")
        # Return empty document to prevent complete failure
        return [Document(page_content=f"No information found for {topic}", metadata={"source": url})]

# === 2. Chunk text ===
def chunk_documents(documents: list[Document]) -> list[Document]:
    splitter = RecursiveCharacterTextSplitter(
        chunk_size=800, chunk_overlap=100,
        separators=["\n\n", "\n", ".", "!", "?"]
    )
    return splitter.split_documents(documents)

# === 3. Filter using LLM ===
def filter_chunks_with_llm(topic: str, docs: list[Document], llm=None) -> list[Document]:
    if llm is None:
        llm = ChatOpenAI(model_name="gpt-3.5-turbo", temperature=0)
    
    # Create batches of 5 docs each to reduce API calls
    batch_size = 5
    relevant_docs = []
    
    for i in range(0, len(docs), batch_size):
        batch = docs[i:i+batch_size]
        prompts = []
        
        for doc in batch:
            prompts.append(
                f"Is the following text relevant to understanding or translating the topic?\n\n"
                f"Topic: {topic}\n"
                f"Text Chunk: {doc.page_content}\n\n"
                f"Respond with 'Yes' or 'No' only."
            )
            
        # Single batch call instead of individual calls
        responses = [llm.invoke(prompt).content.strip().lower() for prompt in prompts]
        
        for j, response in enumerate(responses):
            if "yes" in response:
                relevant_docs.append(batch[j])
                
    return relevant_docs

# === 4. Main function ===
def get_filtered_rag_context(topic: str) -> str:
    raw_docs = load_clean_wikipedia(topic)
    split_docs = chunk_documents(raw_docs)

    if not split_docs:
        raise ValueError(f"❌ No documents found after splitting for topic: '{topic}'")

    embeddings = OpenAIEmbeddings()
    with TemporaryDirectory() as temp_dir:
        vector_db = Chroma.from_documents(split_docs, embeddings, persist_directory=temp_dir)
        retriever = vector_db.as_retriever(search_kwargs={"k": 8})
        
        top_docs = retriever.get_relevant_documents(topic)
        if not top_docs:
            raise ValueError(f"❌ No relevant documents found for topic: '{topic}'")

        filtered_docs = filter_chunks_with_llm(topic, top_docs)
        if not filtered_docs:
            raise ValueError(f"❌ Filtered docs are empty for topic: '{topic}'")

        return "\n\n".join(doc.page_content for doc in filtered_docs)


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
