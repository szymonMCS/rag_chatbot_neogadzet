/**
 * Chatbot JavaScript - Obsługa popup czatu
 * 
 * Funkcjonalności:
 * - Otwieranie/zamykanie widgetu czatu
 * - Wysyłanie wiadomości do API
 * - Wyświetlanie odpowiedzi i źródeł
 * - Sugerowane pytania
 * - Historia rozmowy
 */

(function() {
    'use strict';

    // ============================================
    // KONFIGURACJA
    // ============================================
    const CONFIG = {
        API_URL: '/api/chat',
        CLEAR_URL: '/api/clear',
        SUGGEST_URL: '/api/suggest',
        SESSION_ID: 'chat_' + Date.now(),
        MAX_HISTORY: 50
    };

    // ============================================
    // ELEMENTY DOM
    // ============================================
    const elements = {
        toggle: document.getElementById('chat-toggle'),
        widget: document.getElementById('chat-widget'),
        close: document.getElementById('chat-close'),
        clear: document.getElementById('chat-clear'),
        messages: document.getElementById('chat-messages'),
        form: document.getElementById('chat-form'),
        input: document.getElementById('chat-input'),
        suggestions: document.getElementById('chat-suggestions'),

        badge: document.getElementById('chat-badge')
    };

    // Stan czatu
    let isOpen = false;
    let isLoading = false;
    let messageHistory = [];

    // ============================================
    // FUNKCJE POMOCNICZE
    // ============================================
    
    /**
     * Pokaż/ukryj badge z powiadomieniem
     */
    function hideBadge() {
        if (elements.badge) {
            elements.badge.style.display = 'none';
        }
    }

    /**
     * Przewiń do najnowszej wiadomości
     */
    function scrollToBottom() {
        elements.messages.scrollTop = elements.messages.scrollHeight;
    }

    /**
     * Sformatuj czas wiadomości
     */
    function formatTime(date = new Date()) {
        return date.toLocaleTimeString('pl-PL', { 
            hour: '2-digit', 
            minute: '2-digit' 
        });
    }

    /**
     * Escapuj HTML aby zapobiec XSS
     */
    function escapeHtml(text) {
        const div = document.createElement('div');
        div.textContent = text;
        return div.innerHTML;
    }

    /**
     * Konwertuj markdown na HTML (uproszczony)
     */
    function markdownToHtml(text) {
        return text
            .replace(/\*\*(.+?)\*\*/g, '<strong>$1</strong>')
            .replace(/\*(.+?)\*/g, '<em>$1</em>')
            .replace(/`(.+?)`/g, '<code>$1</code>')
            .replace(/\n/g, '<br>');
    }

    // ============================================
    // FUNKCJE UI
    // ============================================

    /**
     * Otwórz widget czatu
     */
    function openChat() {
        isOpen = true;
        elements.widget.classList.add('open');
        elements.toggle.classList.add('hidden');
        hideBadge();
        
        // Fokus na input po animacji
        setTimeout(() => {
            elements.input.focus();
        }, 300);
        
        scrollToBottom();
    }

    /**
     * Zamknij widget czatu
     */
    function closeChat() {
        isOpen = false;
        elements.widget.classList.remove('open');
        elements.toggle.classList.remove('hidden');
    }

    /**
     * Pokaż wskaźnik pisania
     */
    function showTypingIndicator() {
        const indicator = document.createElement('div');
        indicator.className = 'message assistant-message typing';
        indicator.id = 'typing-indicator';
        indicator.innerHTML = `
            <div class="typing-indicator">
                <span></span>
                <span></span>
                <span></span>
            </div>
        `;
        elements.messages.appendChild(indicator);
        scrollToBottom();
    }

    /**
     * Ukryj wskaźnik pisania
     */
    function hideTypingIndicator() {
        const indicator = document.getElementById('typing-indicator');
        if (indicator) {
            indicator.remove();
        }
    }

    /**
     * Dodaj wiadomość do czatu
     */
    function addMessage(content, role) {
        const messageDiv = document.createElement('div');
        messageDiv.className = `message ${role}-message`;
        
        const time = formatTime();
        const formattedContent = markdownToHtml(escapeHtml(content));
        
        messageDiv.innerHTML = `
            <div class="message-content">
                ${formattedContent}
            </div>
            <div class="message-time">${time}</div>
        `;
        
        elements.messages.appendChild(messageDiv);
        scrollToBottom();
        
        // Zapisz w historii
        messageHistory.push({ role, content, time });
        if (messageHistory.length > CONFIG.MAX_HISTORY) {
            messageHistory.shift();
        }
    }

    /**
     * Wyczyść czat
     */
    function clearChat() {
        // Zachowaj tylko wiadomość systemową
        elements.messages.innerHTML = `
            <div class="message system-message">
                <div class="message-content">
                    <p>🗑️ Rozmowa wyczyszczona. Jak mogę Ci pomóc?</p>
                </div>
            </div>
        `;
        
        messageHistory = [];
        
        // Wyślij żądanie wyczyszczenia na serwerze
        fetch(CONFIG.CLEAR_URL, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ session_id: CONFIG.SESSION_ID })
        }).catch(err => console.error('Błąd czyszczenia:', err));
    }

    // ============================================
    // KOMUNIKACJA Z API
    // ============================================

    /**
     * Wyślij wiadomość do API
     */
    async function sendMessage(message) {
        if (isLoading || !message.trim()) return;
        
        isLoading = true;
        elements.input.disabled = true;
        elements.form.querySelector('.chat-send-btn').disabled = true;
        
        // Dodaj wiadomość użytkownika
        addMessage(message, 'user');
        elements.input.value = '';
        
        // Pokaż wskaźnik pisania
        showTypingIndicator();
        
        try {
            const response = await fetch(CONFIG.API_URL, {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json'
                },
                body: JSON.stringify({
                    message: message,
                    session_id: CONFIG.SESSION_ID
                })
            });
            
            if (!response.ok) {
                throw new Error(`HTTP ${response.status}: ${response.statusText}`);
            }
            
            const data = await response.json();
            
            // Ukryj wskaźnik pisania
            hideTypingIndicator();
            
            // Dodaj odpowiedź asystenta
            addMessage(data.response, 'assistant');
            
        } catch (error) {
            hideTypingIndicator();
            console.error('Błąd:', error);
            addMessage(
                'Przepraszam, wystąpił błąd podczas przetwarzania zapytania. Spróbuj ponownie później.',
                'assistant'
            );
        } finally {
            isLoading = false;
            elements.input.disabled = false;
            elements.form.querySelector('.chat-send-btn').disabled = false;
            elements.input.focus();
        }
    }

    /**
     * Pobierz sugerowane pytania
     */
    async function loadSuggestions() {
        try {
            const response = await fetch(CONFIG.SUGGEST_URL);
            if (!response.ok) return;
            
            const data = await response.json();
            if (!data.suggestions || data.suggestions.length === 0) return;
            
            // Weź pierwsze 3 sugestie
            const suggestions = data.suggestions.slice(0, 3);
            
            elements.suggestions.innerHTML = suggestions.map(q => `
                <button class="suggestion-btn" data-question="${escapeHtml(q)}">
                    ${escapeHtml(q)}
                </button>
            `).join('');
            
            // Dodaj event listenery
            elements.suggestions.querySelectorAll('.suggestion-btn').forEach(btn => {
                btn.addEventListener('click', (e) => {
                    const question = e.target.dataset.question;
                    sendMessage(question);
                });
            });
            
        } catch (error) {
            console.error('Błąd ładowania sugestii:', error);
        }
    }

    // ============================================
    // EVENT LISTENERY
    // ============================================

    function initEventListeners() {
        // Otwieranie/zamykanie
        elements.toggle.addEventListener('click', openChat);
        elements.close.addEventListener('click', closeChat);
        
        // Czyszczenie
        elements.clear.addEventListener('click', clearChat);
        

        
        // Formularz
        elements.form.addEventListener('submit', (e) => {
            e.preventDefault();
            const message = elements.input.value.trim();
            if (message) {
                sendMessage(message);
            }
        });
        
        // Sugestie (delegacja zdarzeń)
        elements.suggestions.addEventListener('click', (e) => {
            if (e.target.classList.contains('suggestion-btn')) {
                const question = e.target.dataset.question;
                sendMessage(question);
            }
        });
        
        // Skróty klawiszowe
        document.addEventListener('keydown', (e) => {
            // ESC zamyka czat
            if (e.key === 'Escape' && isOpen) {
                closeChat();
            }
            
            // / otwiera czat
            if (e.key === '/' && !isOpen && document.activeElement.tagName !== 'INPUT') {
                e.preventDefault();
                openChat();
            }
        });
    }

    // ============================================
    // INICJALIZACJA
    // ============================================

    function init() {
        // Sprawdź czy wszystkie elementy istnieją
        const requiredElements = ['toggle', 'widget', 'close', 'messages', 'form', 'input'];
        for (const name of requiredElements) {
            if (!elements[name]) {
                console.error(`Brakujący element: ${name}`);
                return;
            }
        }
        
        initEventListeners();
        loadSuggestions();
        
        console.log('🤖 Chatbot zainicjalizowany');
        console.log('   Skróty:');
        console.log('   - / : otwórz czat');
        console.log('   - ESC : zamknij czat');
    }

    // Uruchom gdy DOM jest gotowy
    if (document.readyState === 'loading') {
        document.addEventListener('DOMContentLoaded', init);
    } else {
        init();
    }

})();
