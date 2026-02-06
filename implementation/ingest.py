import os
import glob
from langchain_community.document_loaders import DirectoryLoader, TextLoader
from pathlib import Path
from langchain_text_splitters import RecursiveCharacterTextSplitter
from langchain_openai import OpenAIEmbeddings
from langchain_chroma import Chroma
from dotenv import load_dotenv

load_dotenv(override=True)

DB_NAME="vector_db"
MODEL = "gpt-4.1-nano"
embeddings = OpenAIEmbeddings(model="text-embedding-3-large")


def load_multiple_md_files(base_path: str):
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
            file_path = doc.metadata.get('source', '')
            file_name = Path(file_path).stem
            doc.metadata.update({
                "doc_type": doc_type,
                "format": "markdown",
                "file_name": file_name,
                "file_stem": file_name.lower().replace(' ', '_'),
                "category": doc_type,
                "entity_name": file_name
            })
        documents.extend(folder_docs)
        #print(f"{doc_type}: {len(folder_docs)} plików .md")
    #print(f"\nRazem: {len(documents)} dokumentów")
    return documents

docs = load_multiple_md_files("knowledge-base")
#if docs:
#    print(f"\nPrzykład metadanych:")
#    print(f"  Treść: {docs[0].page_content[:100]}...")
#    print(f"  Metadane: {docs[0].metadata}")

def create_chunks(documents, chunk_size = 500, chunk_overlap = 200):
    """
    Dzieli dokumenty na kawałki tak aby każdy miał kawałek wspólny dla niegubienia kontekstu

    Rekursywny spliter textu RecursiveCharacterTextSplitter dzieli tekst inteligentnie hierarchicznie
    
    Args:
        documents: Lista Document do podzielenia
        chunk_size: Docelowy rozmiar fragmentu w znakach
        chunk_overlap: Ile znaków ma się nakładać między chunkami
    
    Returns:
        List[Document]: Lista fragmentów (każdy to Document)
    """
    text_splitter = RecursiveCharacterTextSplitter(
        chunk_size = chunk_size,
        chunk_overlap = chunk_overlap,
        length_function = len,
        separators = ["\n\n", "\n", " ", ""]
    )
    chunks = text_splitter.split_documents(documents)
    #print(f"Podzielono {len(documents)} dokumentów na {len(chunks)} kawałków")
    #print(f"Średni rozmiar kawałka: {sum(len(c.page_content) for c in chunks) / len(chunks):.0f} znaków")
    return chunks

chunks = create_chunks(docs, chunk_size=500, chunk_overlap=200)
#chunks[0].page_content  
#chunks[0].metadata     

def create_embeddings(chunks, embeddings, db_name):
    """
    Tworzy wektorową baze danych

    Args:
        chunks: Lista Document do wektoryzacji
        embeddings: Obiekt embeddingów (OpenAI lub HuggingFace)
        db_name: Nazwa folderu dla bazy (domyślnie "vector_db")
    
    Returns:
        Chroma: Obiekt bazy wektorowej gotowy do wyszukiwania
    """
    if os.path.exists(db_name):
        print("Usuwam starą baze")
        Chroma(persist_directory = db_name, embedding_function = embeddings).delete_collection()
    print(f"Tworze nową baze z {len(chunks)} kawałków...")
    
    vectorstore = Chroma.from_documents(
        documents = chunks,
        embedding = embeddings,
        persist_directory = db_name
    )

    collection = vectorstore._collection
    count = collection.count()
    sample = collection.get(limit = 1, include = ["embeddings"])
    dimensions = len(sample["embeddings"][0])

    #print(f"Baza utworzona: {count:,} wektorów")
    #print(f"Wymiarowość: {dimensions:,} (rozmiar każdego wektora)")
    #print(f"Lokalizacja: ./{db_name}/")

    return vectorstore

vectorstore = create_embeddings(chunks, embeddings, DB_NAME)