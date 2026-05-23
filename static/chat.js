document.addEventListener('DOMContentLoaded', () => {
    const chatForm = document.getElementById('chat-form');
    const chatInput = document.getElementById('chat-input');
    const chatHistory = document.getElementById('chat-history');

    function appendMessage(sender, text, htmlContent = "") {
        const bubble = document.createElement('div');
        bubble.classList.add('chat-bubble', sender === 'user' ? 'user-msg' : 'bot-msg');
        
        let content = `<p>${text}</p>`;
        if (htmlContent) {
            content += htmlContent;
        }
        
        bubble.innerHTML = content;
        chatHistory.appendChild(bubble);
        chatHistory.scrollTop = chatHistory.scrollHeight;
    }

    chatForm.addEventListener('submit', async (e) => {
        e.preventDefault();
        const message = chatInput.value.trim();
        if (!message) return;

        // Add user message to UI
        appendMessage('user', message);
        chatInput.value = '';

        // Add loading state
        const loadingId = 'loading-' + Date.now();
        const loadingBubble = document.createElement('div');
        loadingBubble.id = loadingId;
        loadingBubble.classList.add('chat-bubble', 'bot-msg');
        loadingBubble.innerText = "Curating your profile...";
        chatHistory.appendChild(loadingBubble);
        chatHistory.scrollTop = chatHistory.scrollHeight;

        try {
            const response = await fetch('/api/message', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ message: message })
            });
            const data = await response.json();
            
            // Remove loading state
            document.getElementById(loadingId).remove();

            if (data.error) {
                appendMessage('bot', "System Error: " + data.error);
            } else {
                appendMessage('bot', data.text, data.html);
            }
        } catch (error) {
            document.getElementById(loadingId).remove();
            appendMessage('bot', "Connection error communicating with the backend pipeline.");
        }
    });
});