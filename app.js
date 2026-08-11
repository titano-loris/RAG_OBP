const form = document.getElementById('chatForm');
const input = document.getElementById('messageInput');
const button = document.getElementById('sendButton');
const messages = document.getElementById('messages');
const typingIndicator = document.getElementById('typingIndicator');

let isLoading = false;

function updateControls() {
  button.disabled = isLoading || input.value.trim() === '';
  input.disabled = isLoading;
}

function addMessage(text, role, isError = false) {
  const wrapper = document.createElement('div');
  wrapper.className = `message ${role}${isError ? ' error' : ''}`;
  wrapper.textContent = text;
  messages.appendChild(wrapper);
  messages.scrollTop = messages.scrollHeight;
}

function showTyping(isVisible) {
  typingIndicator.classList.toggle('hidden', !isVisible);
}

form.addEventListener('submit', async (event) => {
  event.preventDefault();
  const text = input.value.trim();
  if (!text || isLoading) {
    return;
  }

  addMessage(text, 'user');
  input.value = '';
  isLoading = true;
  updateControls();
  showTyping(true);

  try {
    const response = await fetch('/api/chat', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ message: text }),
    });

    const data = await response.json();
    if (!response.ok || data.error) {
      addMessage(data.error || 'Une erreur est survenue.', 'assistant', true);
    } else {
      addMessage(data.answer, 'assistant');
    }
  } catch (error) {
    addMessage('Le service est indisponible. Réessayez plus tard.', 'assistant', true);
  } finally {
    isLoading = false;
    updateControls();
    showTyping(false);
  }
});

input.addEventListener('input', updateControls);
updateControls();
