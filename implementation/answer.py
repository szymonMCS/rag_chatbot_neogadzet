from openai import OpenAI
from dotenv import load_dotenv
import logging
import time
from chromadb import PersistentClient
from litellm import completion
from pydantic import BaseModel, Field
from pathlib import Path
from tenacity import retry, wait_exponential, stop_after_attempt


load_dotenv(override=True)

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

MODEL = "openai/gpt-4.1-nano"
DB_NAME = "vector_db"
KNOWLEDGE_BASE_PATH = "knowledge-base/sections"
SUMMARIES_PATH = Path(__file__).parent.parent / "summaries"
collection_name = "docs"
embedding_model = "text-embedding-3-large"

wait = wait_exponential(multiplier=1, min=1, max=10)
stop = stop_after_attempt(3)
openai = OpenAI()

chroma = PersistentClient(path=DB_NAME)
collection = chroma.get_or_create_collection(collection_name)

RETRIEVAL_K = 20
FINAL_K = 10

SYSTEM_PROMPT = """
Jesteś kompetentnym i przyjaznym asystentem reprezentującym sklep z elektroniką NeoGadżet.
Rozmawiasz z użytkownikiem o firmie i oferowanych produktach.
Twoja odpowiedź będzie oceniana pod kątem dokładności, trafności i kompletności, dlatego upewnij się, że odpowiadasz wyłącznie na zadane pytanie i robisz to w sposób wyczerpujący.
Jeśli nie znasz odpowiedzi, poinformuj o tym.
Dla kontekstu, oto konkretne fragmenty z Bazy Wiedzy, które mogą być bezpośrednio związane z pytaniem użytkownika:
{context}

Biorąc pod uwagę ten kontekst, odpowiedz na pytanie użytkownika. Bądź dokładny, merytoryczny i wyczerpujący.
"""

class Result(BaseModel):
    page_content: str
    metadata: dict


class RankOrder(BaseModel):
    order: list[int] = Field(
        description="Kolejność istotności fragmentów, od najbardziej istotnych do najmniej istotnych, według numeru identyfikacyjnego fragmentu"
    )


@retry(wait=wait, stop=stop, reraise=True)
def rerank(question, chunks):
    logger.info(f"Rerank: start dla {len(chunks)} chunków")
    start = time.time()
    system_prompt = """
Jesteś osobą dokonującą rerankingu dokumentów.
Otrzymujesz pytanie i listę odpowiednich fragmentów tekstu z zapytania do bazy wiedzy.
Fragmenty są dostarczane w kolejności, w jakiej zostały pobrane; kolejność powinna być przybliżona według trafności, ale możesz ją poprawić.
Musisz uporządkować podane fragmenty według trafności pytania, zaczynając od fragmentu najbardziej trafnego.
Odpowiadaj tylko za pomocą listy uszeregowanych identyfikatorów fragmentów i niczego więcej. Dołącz wszystkie identyfikatory fragmentów, które zostały Ci przekazane, po rerankingu..
"""
    user_prompt = f"Użytkownik zadał następujące pytanie:\n\n{question}\n\nOUporządkuj wszystkie fragmenty tekstu według ich istotności dla pytania, od najbardziej do najmniej istotnego. Uwzględnij wszystkie podane identyfikatory fragmentów, ponownie uporządkowane.\n\n"
    user_prompt += "Oto kawałki:\n\n"

    for index, chunk in enumerate(chunks):
        user_prompt += f"# CHUNK ID: {index + 1}:\n\n{chunk.page_content}\n\n"

    user_prompt += "Odpowiedz tylko listą identyfikatorów uporządkowanych fragmentów, niczym więcej."

    messages = [
        {"role": "system", "content": system_prompt},
        {"role": "user", "content": user_prompt},
    ]

    response = completion(model=MODEL, messages=messages, response_format=RankOrder, timeout=30, max_retries=0)
    reply = response.choices[0].message.content
    order = RankOrder.model_validate_json(reply).order

    logger.info(f"Rerank: zakończono w {time.time()-start:.2f}s, order={order}")
    # Zabezpieczenie przed pustą listą lub błędnymi indeksami
    if not order or not chunks:
        logger.warning("Rerank: pusta lista order lub chunks, zwracam oryginalne chunks")
        return chunks
    # Filtruj tylko prawidłowe indeksy
    valid_chunks = []
    for i in order:
        if 1 <= i <= len(chunks):
            valid_chunks.append(chunks[i - 1])
    return valid_chunks if valid_chunks else chunks

@retry(wait=wait, stop=stop, reraise=True)
def rewrite_query(question, history=[]):
    """Przepisz pytanie użytkownika, tak aby było bardziej szczegółowe i aby miało większą szansę na znalezienie odpowiedniej treści w Bazie wiedzy."""
    message = f"""
Rozmawiasz z użytkownikiem, odpowiadając na pytania dotyczące sklepu elektronicznego NeoGadżet.
Zamierzasz wyszukać informacje w Bazie Wiedzy, aby odpowiedzieć na pytanie użytkownika.

Oto historia Twojej dotychczasowej rozmowy z użytkownikiem:
{history}

A oto aktualne pytanie użytkownika::
{question}

Odpowiadaj tylko krótkim, precyzyjnym pytaniem, które posłuży Ci do przeszukiwania bazy wiedzy.
Powinno to być BARDZO krótkie i konkretne pytanie, które najprawdopodobniej ujawni treść. Skoncentruj się na szczegółach pytania.
WAŻNE: Odpowiadaj TYLKO, zadając konkretne pytanie z bazy wiedzy, nic więcej.
"""
    logger.info(f"Rewrite query: start")
    start = time.time()
    response = completion(model=MODEL, messages=[{"role": "system", "content": message}], timeout=30, max_retries=0)
    result = response.choices[0].message.content
    logger.info(f"Rewrite query: zakończono w {time.time()-start:.2f}s")
    return result


def merge_chunks(chunks, reranked):
    merged = chunks[:]
    existing = [chunk.page_content for chunk in chunks]
    for chunk in reranked:
        if chunk.page_content not in existing:
            merged.append(chunk)
    return merged


def fetch_context_unranked(question):
    query = openai.embeddings.create(model=embedding_model, input=[question]).data[0].embedding
    results = collection.query(query_embeddings=[query], n_results=RETRIEVAL_K)
    chunks = []
    for result in zip(results["documents"][0], results["metadatas"][0]):
        chunks.append(Result(page_content=result[0], metadata=result[1]))
    return chunks


def fetch_context(original_question):
    logger.info(f"Fetch context: start dla '{original_question[:50]}...'")
    start = time.time()
    rewritten_question = rewrite_query(original_question)
    chunks1 = fetch_context_unranked(original_question)
    logger.info(f"Fetch context: znaleziono {len(chunks1)} chunks dla oryginalnego zapytania")
    chunks2 = fetch_context_unranked(rewritten_question)
    logger.info(f"Fetch context: znaleziono {len(chunks2)} chunks dla przepisanego zapytania")
    chunks = merge_chunks(chunks1, chunks2)
    logger.info(f"Fetch context: po merge {len(chunks)} chunks")
    if not chunks:
        logger.warning("Fetch context: BRAK CHUNKÓW W BAZIE!")
        return []
    reranked = rerank(original_question, chunks)
    logger.info(f"Fetch context: zakończono w {time.time()-start:.2f}s")
    return reranked[:FINAL_K]

def make_rag_messages(question, history, chunks):
    context = "\n\n".join(
        f"Extract from {chunk.metadata['source']}:\n{chunk.page_content}" for chunk in chunks
    )
    system_prompt = SYSTEM_PROMPT.format(context=context)
    return (
        [{"role": "system", "content": system_prompt}]
        + history
        + [{"role": "user", "content": question}]
    )

@retry(wait=wait, stop=stop, reraise=True)
def answer_question(question: str, history: list[dict] = []) -> tuple[str, list]:
    """
    Odpowiedz na pytanie za pomocą RAG i zwróć odpowiedź oraz pobrany kontekst
    """
    logger.info(f"Answer: start dla '{question[:50]}...'")
    start = time.time()
    chunks = fetch_context(question)
    messages = make_rag_messages(question, history, chunks)
    response = completion(model=MODEL, messages=messages, timeout=30, max_retries=0)
    result = response.choices[0].message.content
    logger.info(f"Answer: zakończono w {time.time()-start:.2f}s")
    return result, chunks
