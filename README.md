# 🤖 RAG Chatbot - NeoGadżet

Inteligentny chatbot oparty na architekturze RAG (Retrieval-Augmented Generation) dla sklepu z elektroniką NeoGadżet. Aplikacja umożliwia użytkownikom zadawanie pytań dotyczących produktów, zwrotów, dostawy i innych aspektów oferty sklepu.

![Python](https://img.shields.io/badge/Python-3.10+-blue.svg)
![Flask](https://img.shields.io/badge/Flask-3.0+-green.svg)
![OpenAI](https://img.shields.io/badge/OpenAI-API-orange.svg)
![ChromaDB](https://img.shields.io/badge/ChromaDB-VectorDB-purple.svg)

## ✨ Funkcjonalności

- **💬 Interaktywny czat** - Intuicyjny interfejs czatu z sugerowanymi pytaniami
- **🔍 Inteligentne wyszukiwanie** - Zaawansowany RAG z przepisywaniem zapytań i rerankingiem
- **📚 Baza wiedzy** - Łatwe zarządzanie dokumentacją produktów i regulaminami
- **🎯 Kontekstowe odpowiedzi** - Odpowiedzi oparte na rzeczywistej bazie wiedzy ze źródłami
- **💾 Sesje czatu** - Zapamiętywanie historii rozmów
- **🔌 REST API** - Pełne API do integracji z innymi systemami

## 🏗️ Architektura

```
┌─────────────┐     ┌─────────────┐     ┌─────────────┐
│   Użytkownik │────▶│   Flask App │────▶│  RAG Engine │
└─────────────┘     └─────────────┘     └──────┬──────┘
                                               │
                    ┌─────────────┐     ┌──────▼──────┐
                    │  OpenAI API │◀────│ ChromaDB    │
                    │  (GPT-4.1)  │     │ (wektory)   │
                    └─────────────┘     └─────────────┘
```

### Klucjowe komponenty RAG:

1. **Query Rewriting** - LLM przepisuje pytania użytkownika dla lepszego wyszukiwania
2. **Dual Retrieval** - Wyszukiwanie zarówno oryginalnego, jak i przepisanego zapytania
3. **Re-ranking** - Ponowne sortowanie wyników na podstawie trafności
4. **Context Assembly** - Tworzenie kontekstu z najlepszych fragmentów dokumentów

## 🚀 Szybki start

### Wymagania

- Python 3.10+
- Klucz API OpenAI
- ~500MB wolnego miejsca (modele embeddingów)

### Instalacja

1. **Sklonuj repozytorium:**
```bash
git clone <url-repozytorium>
cd rag_chatbot
```

2. **Utwórz środowisko wirtualne:**
```bash
python -m venv .venv
.venv\Scripts\activate  # Windows
# lub
source .venv/bin/activate  # Linux/Mac
```

3. **Zainstaluj zależności:**
```bash
pip install -r requirements.txt
```

4. **Skonfiguruj zmienne środowiskowe:**
```bash
cp .env.example .env
# Edytuj .env i dodaj swój klucz API OpenAI
```

Przykładowy plik `.env`:
```env
OPENAI_API_KEY=twój-klucz-api-openai
SECRET_KEY=twój-tajny-klucz-flask
PORT=5000
FLASK_DEBUG=true
```

5. **Przygotuj bazę wiedzy:**
   - Umieść pliki Markdown w folderze `knowledge-base/sections/`
   - Struktura folderów określa typ dokumentu (np. `products/`, `policies/`)

6. **Zbuduj bazę wektorową:**
```bash
python implementation/ingest.py
```

7. **Uruchom aplikację:**
```bash
python app.py
```

Aplikacja będzie dostępna pod adresem: `http://localhost:5000`

## 📖 Dokumentacja API

### Endpointy

| Metoda | Endpoint | Opis |
|--------|----------|------|
| GET | `/` | Strona główna z czatem |
| POST | `/api/chat` | Wysłanie wiadomości do chatbota |
| POST | `/api/clear` | Wyczyszczenie historii sesji |
| GET | `/api/health` | Sprawdzenie statusu aplikacji |
| GET | `/api/suggest` | Pobranie sugerowanych pytań |

### Przykład użycia API

```bash
# Wysłanie wiadomości
curl -X POST http://localhost:5000/api/chat \
  -H "Content-Type: application/json" \
  -d '{"message": "Ile kosztuje dostawa?", "session_id": "user123"}'

# Odpowiedź:
{
  "response": "Dostawa do paczkomatu kosztuje 12.99 zł...",
  "sources": [
    {
      "type": "policies",
      "source": "knowledge-base/sections/policies/dostawa.md",
      "content": "Koszty dostawy: Paczkomat InPost - 12.99 zł..."
    }
  ],
  "session_id": "user123"
}
```

## 📁 Struktura projektu

```
rag_chatbot/
├── app.py                    # Główna aplikacja Flask
├── requirements.txt          # Zależności Python
├── .env                      # Zmienne środowiskowe
├── .env.example              # Przykład konfiguracji
├── README.md                 # Ten plik
│
├── implementation/           # Logika RAG
│   ├── ingest.py            # Przetwarzanie dokumentów
│   └── answer.py            # Silnik odpowiedzi
│
├── knowledge-base/          # Baza wiedzy
│   └── sections/            # Dokumenty źródłowe (Markdown)
│       ├── products/        # Opisy produktów
│       ├── policies/        # Regulaminy
│       └── faq/             # FAQ
│
├── vector_db/               # Baza wektorowa ChromaDB
├── preprocessed_db/         # Przetworzone dokumenty
│
├── templates/               # Szablony HTML
│   └── index.html           # Interfejs czatu
│
└── static/                  # Pliki statyczne (CSS, JS)
```

## 🔧 Konfiguracja

### Kluczowe zmienne środowiskowe

| Zmienna | Opis | Domyślnie |
|---------|------|-----------|
| `OPENAI_API_KEY` | Klucz API OpenAI (wymagane) | - |
| `SECRET_KEY` | Klucz bezpieczeństwa Flask | `dev-secret-key` |
| `PORT` | Port serwera | `5000` |
| `FLASK_DEBUG` | Tryb debugowania | `true` |

### Dostosowanie modelu

W pliku `implementation/answer.py` możesz zmienić:

```python
MODEL = "openai/gpt-4.1-nano"  # Model LLM
embedding_model = "text-embedding-3-large"  # Model embeddingów
RETRIEVAL_K = 20  # Liczba pobieranych dokumentów
FINAL_K = 10      # Liczba dokumentów w kontekście
```

## 📝 Zarządzanie bazą wiedzy

### Dodawanie nowych dokumentów

1. Utwórz lub edytuj pliki `.md` w `knowledge-base/sections/`
2. Umieść je w odpowiednich podfolderach (np. `products/`, `policies/`)
3. Uruchom ponownie `ingest.py`:

```bash
python implementation/ingest.py
```

### Format dokumentów

```markdown
# Tytuł dokumentu

Treść dokumentu w formacie Markdown...

## Sekcja 1
Szczegóły...

## Sekcja 2
Więcej informacji...
```

## 🧪 Testowanie

```bash
# Sprawdź status aplikacji
curl http://localhost:5000/api/health

# Wyślij testowe zapytanie
curl -X POST http://localhost:5000/api/chat \
  -H "Content-Type: application/json" \
  -d '{"message": "Cześć!"}'
```

## 🛠️ Rozwiązywanie problemów

### Błąd: "Baza wektorowa nie istnieje"
```bash
python implementation/ingest.py
```

### Błąd API OpenAI
- Sprawdź poprawność `OPENAI_API_KEY` w pliku `.env`
- Upewnij się, że masz wystarczające środki na koncie OpenAI

### Problemy z zależnościami
```bash
pip install --upgrade -r requirements.txt
```

## 📄 Licencja

Projekt dostępny na licencji MIT.

## 🙏 Podziękowania

- [LangChain](https://langchain.com/) - Framework RAG
- [ChromaDB](https://www.trychroma.com/) - Baza wektorowa
- [OpenAI](https://openai.com/) - Modele LLM
- [Flask](https://flask.palletsprojects.com/) - Framework webowy

---

Stworzone z ❤️ dla NeoGadżet
