import os
import glob
from langchain_community.document_loaders import DirectoryLoader, TextLoader
from pathlib import Path
from langchain_text_splitters import RecursiveCharacterTextSplitter
from langchain_openai import OpenAIEmbeddings
from langchain_chroma import Chroma
from dotenv import load_dotenv

load_dotenv(override=True)

DB_NAME = "vector_db"
KNOWLEDGE_BASE = "knowledge-base/sections"
MODEL = "gpt-4.1-nano"
embeddings = OpenAIEmbeddings(model="text-embedding-3-large")


def fetch_documents(base_path: str):
    """
    Wczytujemy kilka plików .md z danymi

    Returns:
        List[Document]: Lista dokumentów z metadanymi
    """
    documents = []
    folders = [f for f in glob.glob(f"{base_path}/*") if os.path.isdir(f)]

    for folder in folders:
        doc_type = os.path.basename(folder)
        loader = DirectoryLoader(
            folder,
            glob = "**/*.md",
            loader_cls = TextLoader,
            loader_kwargs = {"encoding": "utf-8"},
            recursive = True
        )
        folder_docs = loader.load()
        for doc in folder_docs:
            doc.metadata["doc_type"] = doc_type
            documents.append(doc)
    return documents

def create_chunks(documents, chunk_size = 500, chunk_overlap = 200):
    text_splitter = RecursiveCharacterTextSplitter(
        chunk_size = chunk_size,
        chunk_overlap = chunk_overlap,
    )
    chunks = text_splitter.split_documents(documents)
    return chunks   

def create_embeddings(chunks):
    """
    Tworzy wektorową baze danych

    Args:
        chunks: Lista Document do wektoryzacji
        embeddings: Obiekt embeddingów (OpenAI lub HuggingFace)
        db_name: Nazwa folderu dla bazy (domyślnie "vector_db")
    
    Returns:
        Chroma: Obiekt bazy wektorowej gotowy do wyszukiwania
    """
    if os.path.exists(DB_NAME):
        print("Usuwam starą baze")
        Chroma(persist_directory = DB_NAME, embedding_function = embeddings).delete_collection()
    
    vectorstore = Chroma.from_documents(
        documents = chunks,
        embedding = embeddings,
        persist_directory = DB_NAME
    )

    collection = vectorstore._collection
    count = collection.count()
    sample_embedding = collection.get(limit=1, include=["embeddings"])["embeddings"][0]
    dimensions = len(sample_embedding)
    print(f"There are {count:,} vectors with {dimensions:,} dimensions in the vector store")
    return vectorstore
