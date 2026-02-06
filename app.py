import os
import json
from datetime import datetime
from flask import Flask, render_template, request, jsonify
from flask_cors import CORS

from implementation.answer import answer_question, collection

app = Flask(__name__)
CORS(app)

app.config['SECRET_KEY'] = os.getenv('SECRET_KEY', 'dev-secret-key')

chat_sessions = {}


@app.route('/')
def index():
    """Strona główna z demo produktu i popup chatbotem."""
    return render_template('index.html')


@app.route('/api/chat', methods=['POST'])
def chat():
    """
    Endpoint API do obsługi wiadomości czatu.
    
    Oczekuje JSON:
    {
        "message": "tekst wiadomości",
        "session_id": "opcjonalne-id-sesji"
    }
    
    Zwraca JSON:
    {
        "response": "odpowiedź asystenta",
        "sources": [...],
        "session_id": "id-sesji"
    }
    """
    try:
        data = request.get_json()
        
        if not data or 'message' not in data:
            return jsonify({'error': 'Brak wiadomości'}), 400
        
        user_message = data['message'].strip()
        session_id = data.get('session_id', 'default')
        
        if not user_message:
            return jsonify({'error': 'Pusta wiadomość'}), 400
        
        if session_id not in chat_sessions:
            chat_sessions[session_id] = []
        
        history = chat_sessions[session_id]
        
        # Dodaj wiadomość użytkownika do historii
        history.append({
            'role': 'user',
            'content': user_message,
            'timestamp': datetime.now().isoformat()
        })
        
        # Pobierz odpowiedź od RAG
        response_text, chunks = answer_question(user_message, history)
        
        # Konwertuj chunki na format źródeł dla frontendu
        sources = []
        for chunk in chunks:
            sources.append({
                'type': chunk.metadata.get('type', 'dokument'),
                'source': chunk.metadata.get('source', 'nieznane'),
                'content': chunk.page_content[:200] + '...' if len(chunk.page_content) > 200 else chunk.page_content
            })
        
        # Dodaj odpowiedź asystenta do historii
        history.append({
            'role': 'assistant',
            'content': response_text,
            'timestamp': datetime.now().isoformat()
        })
        
        # Ogranicz historię do ostatnich 20 wiadomości
        chat_sessions[session_id] = history[-20:]
        
        return jsonify({
            'response': response_text,
            'sources': sources,
            'session_id': session_id,
            'timestamp': datetime.now().isoformat()
        })
        
    except Exception as e:
        app.logger.error(f'Błąd w /api/chat: {e}')
        return jsonify({
            'error': 'Wystąpił błąd podczas przetwarzania zapytania',
            'details': str(e)
        }), 500


@app.route('/api/clear', methods=['POST'])
def clear_chat():
    """Wyczyść historię czatu dla danej sesji."""
    data = request.get_json() or {}
    session_id = data.get('session_id', 'default')
    
    if session_id in chat_sessions:
        chat_sessions[session_id] = []
    
    return jsonify({'status': 'ok', 'message': 'Historia wyczyszczona'})


@app.route('/api/health', methods=['GET'])
def health():
    """Endpoint sprawdzający stan aplikacji."""
    try:
        count = collection.count()
        stats = {
            'documents_count': count,
            'collection_name': collection.name,
            'status': 'ready'
        }
        
        return jsonify({
            'status': 'ok',
            'vector_db': stats,
            'timestamp': datetime.now().isoformat()
        })
    except Exception as e:
        return jsonify({
            'status': 'error',
            'error': str(e)
        }), 503


@app.route('/api/suggest', methods=['GET'])
def suggest_questions():
    """
    Zwróć sugerowane pytania dla użytkownika.
    """
    suggestions = [
        "Ile kosztuje dostawa do paczkomatu?",
        "Jak zwrócić produkt?",
        "Czy słuchawki AeroSound X2 mają ANC?",
        "Jaki jest czas pracy Kamery HomeCam?",
        "Jak zresetować router WiLink?",
        "Co to jest rękojmia?",
        "Czy mogę zrezygnować z zakupu?",
        "Jak długo trwa zwrot pieniędzy?",
    ]
    
    return jsonify({'suggestions': suggestions})


@app.template_filter('from_json')
def from_json(value):
    """Filtr do parsowania JSON w szablonach."""
    try:
        return json.loads(value)
    except:
        return {}


# Error handlers
@app.errorhandler(404)
def not_found(e):
    return jsonify({'error': 'Nie znaleziono'}), 404


@app.errorhandler(500)
def internal_error(e):
    return jsonify({'error': 'Błąd wewnętrzny serwera'}), 500


def init_app():
    """Inicjalizacja aplikacji - sprawdź czy baza wektorowa istnieje."""
    try:
        count = collection.count()
        print(f"[OK] Baza wektorowa gotowa: {count} dokumentow")
    except FileNotFoundError as e:
        print(f"\n{'='*60}")
        print("[!] UWAGA: Baza wektorowa nie istnieje!")
        print(f"{'='*60}")
        print(f"\nAby utworzyc baze, uruchom:")
        print(f"   python implementation/ingest.py")
        print(f"\nBlad: {e}")
        print(f"{'='*60}\n")


if __name__ == '__main__':
    init_app()
    
    port = int(os.getenv('PORT', 5000))
    debug = os.getenv('FLASK_DEBUG', 'true').lower() == 'true'
    
    print(f"\n[START] Uruchamianie aplikacji na http://localhost:{port}")
    print(f"   Debug mode: {debug}\n")
    
    app.run(host='0.0.0.0', port=port, debug=debug)
