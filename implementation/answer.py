from langchain_chroma import Chroma
from langchain_openai import ChatOpenAI, OpenAIEmbeddings
from openai import OpenAI
from dotenv import load_dotenv
from langchain_core.messages import SystemMessage, HumanMessage, convert_to_messages

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

SYSTEM_PROMPT = """
Jesteś kompetentnym i przyjaznym asystentem reprezentującym sklep z elektroniką NeoGadżet.
Rozmawiasz z użytkownikiem o firmie i oferowanych produktach.
Twoja odpowiedź będzie oceniana pod kątem dokładności, trafności i kompletności, dlatego upewnij się, że odpowiadasz wyłącznie na zadane pytanie i robisz to w sposób wyczerpujący.
Jeśli nie znasz odpowiedzi, poinformuj o tym.
Dla kontekstu, oto konkretne fragmenty z Bazy Wiedzy, które mogą być bezpośrednio związane z pytaniem użytkownika:
{context}

Biorąc pod uwagę ten kontekst, odpowiedz na pytanie użytkownika. Bądź dokładny, merytoryczny i wyczerpujący.
"""

def answer_question(question, history = [], retriever = None, llm = None):
    """
    Funkcja RAG pobierająca kontekst i generująca odpowiedź

    Args:
        question: Pytanie użytkownika
        history: Lista poprzednich wiadomości (opcjonalnie)
        retriever: Skonfigurowany retriever do wyszukiwania
        llm: Model językowy
    
    Returns:
        tuple: (odpowiedź, lista_dokumentów)
               Odpowiedź to string, lista_dokumentów to chunki użyte do odpowiedzi
    """
    docs = retriever.invoke(question)
    print(f"Znaleziono {len(docs)} dokumentów dla pytania: '{question}'")

    context = "\n\n".join(doc.page_content for doc in docs)
    print(f"Całkowita długość kontekstu: {len(context)} znaków")

    system_prompt = SYSTEM_PROMPT.format(context = context)
    messages = []
    messages.append(SystemMessage(content = system_prompt))
    if history:
        messages.extend(convert_to_messages(history))
    messages.append(HumanMessage(content = question))
    print("Generowanie odpowiedzi")
    response = llm.invoke(messages)
    return response.content, docs

#odpowiedz, uzyte_dokumenty = answer_question(
#    "Co to NeoGadżet?",
#    retriever=retriever,
#    llm=ChatOpenAI(model = MODEL)
#)
#print(odpowiedz)
