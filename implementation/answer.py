from langchain_chroma import Chroma
from langchain_openai import ChatOpenAI, OpenAIEmbeddings
from openai import OpenAI
from dotenv import load_dotenv

load_dotenv(override=True)

DB_NAME="vector_db"
MODEL = "gpt-4.1-nano"
embeddings = OpenAIEmbeddings(model="text-embedding-3-large")

def setup_retriever(db_name, embeddings, k = 10):
    """
    konfiguracja narzędzia do wyszukiwania podobnych dokumentów

    Args:
        db_name: Ścieżka do folderu z bazą (np. "vector_db")
        embeddings: Obiekt embeddingów (muszą być te same co przy tworzeniu!)
        k: Ile dokumentów zwrócić (domyślnie 10)
    
    Returns:
        Retriever: Obiekt który można wywołać z pytaniem
    """
    vectorstore = Chroma(
        persist_directory = db_name,
        embedding_function = embeddings
    )
    retriever = vectorstore.as_retriever(search_kwargs = {"k": k})
    return retriever

retriever = setup_retriever(DB_NAME, embeddings, k=10)
#docs = retriever.invoke("Jak nazywa się sklep?")
#print(docs[0].page_content)
#print(docs[0].metadata) 

        