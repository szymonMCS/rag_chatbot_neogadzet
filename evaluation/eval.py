"""
Moduł ewaluacji RAG - metryki retrieval i ocena odpowiedzi (LLM-as-a-judge).
"""
import math
from pydantic import BaseModel, Field
from litellm import completion
from dotenv import load_dotenv

from implementation.answer import answer_question, fetch_context


load_dotenv(override=True)

MODEL = "gpt-4.1-nano"


class RetrievalEval(BaseModel):
    """Metryki oceny wydajności wyszukiwania."""

    mrr: float = Field(description="Średnia wzajemna ranga – średnia dla wszystkich słów kluczowych")
    ndcg: float = Field(description="Znormalizowany zdyskontowany skumulowany zysk (istotność binarna)")
    keywords_found: int = Field(description="Liczba słów kluczowych znalezionych w wynikach wyszukiwania Top-K")
    total_keywords: int = Field(description="Całkowita liczba słów kluczowych do znalezienia")
    keyword_coverage: float = Field(description="Procent znalezionych słów kluczowych")


class AnswerEval(BaseModel):
    """Ocena jakości odpowiedzi przez LLM-as-a-judge."""

    feedback: str = Field(
        description="Zwięzła informacja zwrotna na temat jakości odpowiedzi"
    )
    accuracy: float = Field(
        description="Jak bardzo poprawna jest odpowiedź? Od 1 (błędna) do 5 (idealna)"
    )
    completeness: float = Field(
        description="Jak kompletna jest odpowiedź? Od 1 (słaba) do 5 (idealna)"
    )
    relevance: float = Field(
        description="Jak bardzo adekwatna do pytania? Od 1 (słaba) do 5 (idealna)"
    )


def calculate_mrr(keyword: str, retrieved_docs: list) -> float:
    """Oblicz wzajemną rangę dla pojedynczego słowa kluczowego."""
    keyword_lower = keyword.lower()
    for rank, doc in enumerate(retrieved_docs, start=1):
        if keyword_lower in doc.page_content.lower():
            return 1.0 / rank
    return 0.0


def calculate_dcg(relevances: list[int], k: int) -> float:
    """Oblicz zdyskontowany skumulowany zysk."""
    dcg = 0.0
    for i in range(min(k, len(relevances))):
        dcg += relevances[i] / math.log2(i + 2)
    return dcg


def calculate_ndcg(keyword: str, retrieved_docs: list, k: int = 10) -> float:
    """Oblicz nDCG dla pojedynczego słowa kluczowego."""
    keyword_lower = keyword.lower()
    relevances = [
        1 if keyword_lower in doc.page_content.lower() else 0 for doc in retrieved_docs[:k]
    ]
    dcg = calculate_dcg(relevances, k)
    ideal_relevances = sorted(relevances, reverse=True)
    idcg = calculate_dcg(ideal_relevances, k)
    return dcg / idcg if idcg > 0 else 0.0


def evaluate_retrieval(question: str, keywords: list[str], k: int = 10) -> RetrievalEval:
    """
    Oceń wydajność wyszukiwania dla pytania i słów kluczowych.
    
    Args:
        question: Pytanie do przetestowania
        keywords: Lista słów kluczowych do znalezienia
        k: Liczba dokumentów do pobrania
    
    Returns:
        RetrievalEval z metrykami MRR, nDCG i pokrycia słów kluczowych
    """
    retrieved_docs = fetch_context(question)
    
    mrr_scores = [calculate_mrr(keyword, retrieved_docs) for keyword in keywords]
    avg_mrr = sum(mrr_scores) / len(mrr_scores) if mrr_scores else 0.0
    
    ndcg_scores = [calculate_ndcg(keyword, retrieved_docs, k) for keyword in keywords]
    avg_ndcg = sum(ndcg_scores) / len(ndcg_scores) if ndcg_scores else 0.0
    
    keywords_found = sum(1 for score in mrr_scores if score > 0)
    total_keywords = len(keywords)
    keyword_coverage = (keywords_found / total_keywords * 100) if total_keywords > 0 else 0.0
    
    return RetrievalEval(
        mrr=avg_mrr,
        ndcg=avg_ndcg,
        keywords_found=keywords_found,
        total_keywords=total_keywords,
        keyword_coverage=keyword_coverage,
    )


def evaluate_answer(question: str, reference_answer: str = "") -> tuple[AnswerEval, str, list]:
    """
    Oceń jakość odpowiedzi za pomocą metody LLM-as-a-judge.
    
    Args:
        question: Pytanie użytkownika
        reference_answer: Opcjonalna odpowiedź referencyjna do porównania
    
    Returns:
        Krotkę (AnswerEval, wygenerowana odpowiedź, lista pobranych dokumentów)
    """
    generated_answer, retrieved_docs = answer_question(question)
    
    judge_messages = [
        {
            "role": "system",
            "content": "Jesteś ekspertem oceniającym jakość odpowiedzi. Oceń wygenerowaną odpowiedź.",
        },
        {
            "role": "user",
            "content": f"""Pytanie:
{question}

Wygenerowana odpowiedź:
{generated_answer}

Odpowiedź referencyjna:
{reference_answer or "Brak odpowiedzi referencyjnej"}

Oceń wygenerowaną odpowiedź w trzech wymiarach:
1. Dokładność: Jak bardzo jest poprawna pod względem faktów? (1-5)
2. Kompletność: Jak dokładnie odnosi się do wszystkich aspektów pytania? (1-5)
3. Trafność: Jak dobrze odpowiada bezpośrednio na pytanie? (1-5)

Jeśli odpowiedź jest błędna, punktacja dokładności musi wynosić 1.""",
        },
    ]
    
    judge_response = completion(model=MODEL, messages=judge_messages, response_format=AnswerEval)
    answer_eval = AnswerEval.model_validate_json(judge_response.choices[0].message.content)
    
    return answer_eval, generated_answer, retrieved_docs
