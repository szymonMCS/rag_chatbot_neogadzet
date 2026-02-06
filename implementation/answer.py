from langchain_chroma import Chroma
from langchain_openai import ChatOpenAI, OpenAIEmbeddings
from openai import OpenAI
from dotenv import load_dotenv
from langchain_core.messages import SystemMessage, HumanMessage, convert_to_messages
from langchain_core.documents import Document

load_dotenv(override=True)

DB_NAME="vector_db"
MODEL = "gpt-4.1-nano"
RETRIEVAL_K = 10
embeddings = OpenAIEmbeddings(model="text-embedding-3-large")

SYSTEM_PROMPT = """
Jesteś kompetentnym i przyjaznym asystentem reprezentującym sklep z elektroniką NeoGadżet.
Rozmawiasz z użytkownikiem o firmie i oferowanych produktach.
Twoja odpowiedź będzie oceniana pod kątem dokładności, trafności i kompletności, dlatego upewnij się, że odpowiadasz wyłącznie na zadane pytanie i robisz to w sposób wyczerpujący.
Jeśli nie znasz odpowiedzi, poinformuj o tym.
Dla kontekstu, oto konkretne fragmenty z Bazy Wiedzy, które mogą być bezpośrednio związane z pytaniem użytkownika:
{context}

Biorąc pod uwagę ten kontekst, odpowiedz na pytanie użytkownika. Bądź dokładny, merytoryczny i wyczerpujący.
"""

vectorstore = Chroma(persist_directory=DB_NAME, embedding_function=embeddings)
retriever = vectorstore.as_retriever()
llm = ChatOpenAI(temperature=0, model_name=MODEL)

def fetch_context(question: str) -> list[Document]:
    """
    Pobiera odpowiednie dokumenty kontekstowe do pytania
    """
    return retriever.invoke(question, k=RETRIEVAL_K) 

def combined_question(question: str, history: list[dict] = []) -> str:
    """
    Łączy odpowiedzi użytkownika w jeden string
    """
    contents = []
    for m in history:
        if m["role"] == "user":
            content = m["content"]
            if isinstance(content, list):
                content = " ".join(str(x) for x in content)
            contents.append(content)
    prior = "\n".join(contents)
    return prior + "\n" + question

def answer_question(question: str, history: list[dict] = []) -> tuple[str, list[Document]]:
    """
    Funkcja RAG pobierająca kontekst i generująca odpowiedź
    """
    combined = combined_question(question, history)
    docs = fetch_context(combined)
    context = "\n\n".join(doc.page_content for doc in docs)
    system_prompt = SYSTEM_PROMPT.format(context=context)
    messages = [SystemMessage(content=system_prompt)]
    messages.extend(convert_to_messages(history))
    messages.append(HumanMessage(content=question))
    response = llm.invoke(messages)
    return response.content, docs
