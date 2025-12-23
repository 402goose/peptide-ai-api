// Peptide AI Chrome Extension
const API_URL = 'https://peptide-ai-api-production.up.railway.app';
const WEB_URL = 'https://peptide-ai-web-production.up.railway.app';

// Get API key from storage or use default
let API_KEY = '';

// Elements
const chatContainer = document.getElementById('chat-container');
const messageInput = document.getElementById('message-input');
const sendBtn = document.getElementById('send-btn');

// Message history for context
let messages = [];

// Initialize
document.addEventListener('DOMContentLoaded', async () => {
  // Load API key from storage
  const stored = await chrome.storage.sync.get(['apiKey']);
  API_KEY = stored.apiKey || '';

  // Set up event listeners
  sendBtn.addEventListener('click', sendMessage);
  messageInput.addEventListener('keypress', (e) => {
    if (e.key === 'Enter') sendMessage();
  });

  // Quick action buttons
  document.querySelectorAll('.quick-btn').forEach(btn => {
    btn.addEventListener('click', () => {
      messageInput.value = btn.dataset.query;
      sendMessage();
    });
  });
});

async function sendMessage() {
  const message = messageInput.value.trim();
  if (!message) return;

  // Add user message to UI
  addMessage('user', message);
  messageInput.value = '';
  sendBtn.disabled = true;

  // Add to history
  messages.push({ role: 'user', content: message });

  // Show loading
  const loadingEl = addLoading();

  try {
    // Try streaming endpoint first
    const response = await fetch(`${API_URL}/api/v1/chat/stream`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
        'X-API-Key': API_KEY || 'extension-user',
      },
      body: JSON.stringify({
        message,
        history: messages.slice(-10), // Last 10 messages for context
      }),
    });

    if (!response.ok) {
      throw new Error(`API error: ${response.status}`);
    }

    // Handle SSE stream
    const reader = response.body.getReader();
    const decoder = new TextDecoder();
    let fullContent = '';
    let sources = [];

    // Remove loading, add empty assistant message
    loadingEl.remove();
    const assistantMsg = addMessage('assistant', '');
    const bubble = assistantMsg.querySelector('.bubble');

    while (true) {
      const { done, value } = await reader.read();
      if (done) break;

      const chunk = decoder.decode(value, { stream: true });
      const lines = chunk.split('\n');

      for (const line of lines) {
        if (line.startsWith('data: ')) {
          try {
            const data = JSON.parse(line.slice(6));

            if (data.type === 'content' && data.content) {
              fullContent += data.content;
              bubble.innerHTML = formatMarkdown(fullContent);
            } else if (data.type === 'sources' && data.sources) {
              sources = data.sources;
            } else if (data.type === 'done') {
              // Add sources if any
              if (sources.length > 0) {
                const sourcesHtml = formatSources(sources);
                bubble.innerHTML += sourcesHtml;
              }
            }
          } catch (e) {
            // Ignore parse errors
          }
        }
      }

      // Auto-scroll
      chatContainer.scrollTop = chatContainer.scrollHeight;
    }

    // Add to history
    messages.push({ role: 'assistant', content: fullContent });

  } catch (error) {
    console.error('Error:', error);
    loadingEl.remove();
    addMessage('assistant', 'Sorry, I had trouble connecting. Please try again or <a href="' + WEB_URL + '" target="_blank">use the full app</a>.');
  } finally {
    sendBtn.disabled = false;
    messageInput.focus();
  }
}

function addMessage(role, content) {
  const div = document.createElement('div');
  div.className = `message ${role}`;
  div.innerHTML = `<div class="bubble">${formatMarkdown(content)}</div>`;
  chatContainer.appendChild(div);
  chatContainer.scrollTop = chatContainer.scrollHeight;
  return div;
}

function addLoading() {
  const div = document.createElement('div');
  div.className = 'message assistant';
  div.innerHTML = `
    <div class="loading">
      <span></span>
      <span></span>
      <span></span>
    </div>
  `;
  chatContainer.appendChild(div);
  chatContainer.scrollTop = chatContainer.scrollHeight;
  return div;
}

function formatMarkdown(text) {
  if (!text) return '';

  return text
    // Bold
    .replace(/\*\*(.*?)\*\*/g, '<strong>$1</strong>')
    // Headers
    .replace(/^### (.*$)/gm, '<strong style="color:#60a5fa">$1</strong>')
    .replace(/^## (.*$)/gm, '<strong style="color:#60a5fa;font-size:15px">$1</strong>')
    // Lists
    .replace(/^- (.*$)/gm, '• $1')
    // Line breaks
    .replace(/\n/g, '<br>');
}

function formatSources(sources) {
  if (!sources || sources.length === 0) return '';

  const sourceItems = sources.slice(0, 3).map((s, i) => {
    const badge = s.type === 'pubmed' ? 'PubMed' : s.type === 'reddit' ? 'Reddit' : s.type;
    const url = s.url || '#';
    return `
      <div class="source">
        <span class="source-badge">${badge}</span>
        <a href="${url}" target="_blank" style="color:#64748b;text-decoration:none;overflow:hidden;text-overflow:ellipsis;white-space:nowrap;">
          ${s.title.slice(0, 40)}...
        </a>
      </div>
    `;
  }).join('');

  return `<div class="sources"><strong style="font-size:11px;color:#64748b">Sources:</strong>${sourceItems}</div>`;
}
