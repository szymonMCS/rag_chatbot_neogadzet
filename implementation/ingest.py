from pathlib import Path
from openai import OpenAI
from dotenv import load_dotenv
from pydantic import BaseModel, Field
from chromadb import PersistentClient
from tqdm import tqdm
from litellm import completion
from multiprocessing import Pool
from tenacity import retry, wait_exponential


load_dotenv(override=True)

MODEL = "openai/gpt-4.1-nano"
collection_name = "docs"
embedding_model = "text-embedding-3-large"
DB_NAME = "vector_db"
KNOWLEDGE_BASE_PATH = Path(__file__).parent.parent / "knowledge-base" / "sections"
AVERAGE_CHUNK_SIZE = 100
wait = wait_exponential(multiplier=1, min=10, max=240)


WORKERS = 3

openai = OpenAI()

class Result(BaseModel):
    page_content: str
    metadata: dict

class Chunk(BaseModel):
    headline: str = Field(description = "Nagłówek prawdopodobnie będzie użyty w zapytaniu")
    summary: str = Field(description = "Podsumowanie zawartości fragmentu")
    original_text: str = Field(description = "Oryginalna zawartość fragmentu")

    def as_result(self, document):
        metadata = {"source": document["source"], "type": document["type"]}
        return Result(
            page_content=self.headline + "\n\n" + self.summary + "\n\n" + self.original_text,
            metadata=metadata,
        )

class Chunks(BaseModel):
    """kolekcja chunków"""
    chunks: list[Chunk]

def fetch_documents():
    documents = []

    for file in KNOWLEDGE_BASE_PATH.rglob("*.md"):
        doc_type = file.parent.name
        with open(file, "r", encoding="utf-8") as f:
            documents.append({"type": doc_type, "source": file.as_posix(), "text": f.read()})

    print(f"Loaded {len(documents)} documents")
    return documents

def make_prompt(document, average_chunk_size = 500):
    how_many = (len(document["text"]) // average_chunk_size) + 1
    return f"""
Twoim zadaniem jest pobranie dokumentu i podzielenie go na nakładające się na siebie fragmenty (chunki) do Bazy Wiedzy.

Dokument pochodzi z zasobów wewnętrznych sklepu z elektroniką o nazwie NeoGadżet.
Typ dokumentu: {document["type"]}
Dokument został pobrany z: {document["source"]}

Chatbot będzie wykorzystywał te fragmenty do odpowiadania na pytania dotyczące firmy oraz oferowanego sprzętu.
Podziel dokument według własnego uznania, upewniając się, że cała treść dokumentu została uwzględniona we fragmentach – nie pomijaj żadnych informacji.

Dokument ten powinien zostać podzielony na co najmniej {how_many} fragmentów, ale możesz utworzyć ich więcej lub mniej, jeśli będzie to uzasadnione strukturą tekstu.
Pomiędzy fragmentami musi występować zakładka (overlap) wynosząca około 25% długości lub ~50 słów.

Dla każdego fragmentu podaj:
1. headline - krótki nagłówek odpowiadający potencjalnemu zapytaniu użytkownika
2. summary - kilka zdań podsumowujących treść
3. original_text - dokładny, oryginalny tekst fragmentu

Dokument:{document["text"]}

Zwróć fragmenty w formacie JSON.
"""

def make_messages(document):
    return [
        {"role": "user", "content": make_prompt(document)},
    ]


@retry(wait=wait)
def process_document(document):
    messages = make_messages(document)
    response = completion(model=MODEL, messages=messages, response_format=Chunks)
    reply = response.choices[0].message.content
    doc_as_chunks = Chunks.model_validate_json(reply).chunks
    return [chunk.as_result(document) for chunk in doc_as_chunks]


def create_chunks(documents):
    chunks = []
    with Pool(processes=WORKERS) as pool:
        for result in tqdm(pool.imap_unordered(process_document, documents), total=len(documents)):
            chunks.extend(result)
    return chunks


def create_embeddings(chunks):
    chroma = PersistentClient(path=DB_NAME)
    if collection_name in [c.name for c in chroma.list_collections()]:
        chroma.delete_collection(collection_name)

    texts = [chunk.page_content for chunk in chunks]
    
    emb = openai.embeddings.create(model=embedding_model, input=texts).data
    vectors = [e.embedding for e in emb]

    collection = chroma.get_or_create_collection(collection_name)

    ids = [str(i) for i in range(len(chunks))]
    metas = [chunk.metadata for chunk in chunks]

    collection.add(ids=ids, embeddings=vectors, documents=texts, metadatas=metas)
    print(f"Vectorstore utworzony z {collection.count()} dokumentów")


if __name__ == "__main__":
    documents = fetch_documents()
    chunks = create_chunks(documents)
    create_embeddings(chunks)
    print("Przetwarzanie danych zakończone")




