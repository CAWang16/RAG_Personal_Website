// chat.js — Chat widget with SSE streaming

const API_URL = '/api/chat';

const panel      = document.getElementById('chat-panel');
const toggle     = document.getElementById('chat-toggle');
const iconOpen   = document.getElementById('chat-icon-open');
const iconClose  = document.getElementById('chat-icon-close');
const messages   = document.getElementById('chat-messages');
const input      = document.getElementById('chat-input');
const sendBtn    = document.getElementById('chat-send');
const suggestions = document.getElementById('suggested-questions');

let history = [];   // [{role, content}, ...]
let isStreaming = false;

// ── Toggle panel ─────────────────────────────────────────────────────────────
toggle.addEventListener('click', () => {
  const open = panel.classList.toggle('open');
  iconOpen.style.display  = open ? 'none'  : 'block';
  iconClose.style.display = open ? 'block' : 'none';
  if (open) input.focus();
  toggle.classList.add('no-pulse');
  const hint = document.getElementById('chat-hint');
  if (hint) hint.remove();
});

// ── Suggested questions ───────────────────────────────────────────────────────
document.querySelectorAll('.suggestion').forEach(btn => {
  btn.addEventListener('click', () => {
    if (isStreaming) return;
    const text = btn.textContent;
    suggestions.remove();
    sendMessage(text);
  });
});

// ── Send on Enter / button click ──────────────────────────────────────────────
sendBtn.addEventListener('click', submit);
input.addEventListener('keydown', e => { if (e.key === 'Enter' && !e.shiftKey) submit(); });

function submit() {
  const text = input.value.trim();
  if (!text || isStreaming) return;
  input.value = '';
  if (suggestions && suggestions.parentNode) suggestions.remove();
  sendMessage(text);
}

// ── Core send + SSE stream ────────────────────────────────────────────────────
async function sendMessage(text) {
  appendMessage('user', text);
  history.push({ role: 'user', content: text });

  const typingEl = appendMessage('assistant', '', true);
  setStreaming(true);

  try {
    const response = await fetch(API_URL, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ message: text, history: history.slice(-8) }),
    });

    if (!response.ok) {
      const err = await response.json().catch(() => ({}));
      const msg = response.status === 429
        ? (err.detail || "Too many requests — please slow down.")
        : (err.detail || `HTTP ${response.status}`);
      throw new Error(msg);
    }

    const reader  = response.body.getReader();
    const decoder = new TextDecoder();
    let   buffer  = '';
    let   full    = '';

    while (true) {
      const { done, value } = await reader.read();
      if (done) break;

      buffer += decoder.decode(value, { stream: true });
      const lines = buffer.split('\n');
      buffer = lines.pop();          // keep incomplete last line

      for (const line of lines) {
        if (!line.startsWith('data: ')) continue;
        const payload = line.slice(6);
        if (payload === '[DONE]') break;
        if (payload.startsWith('[ERROR]')) throw new Error(payload.slice(8));
        full += payload;
        typingEl.querySelector('.md-content').innerHTML = marked.parse(full);
        scrollToBottom();
      }
    }

    typingEl.classList.remove('typing');
    typingEl.querySelector('.md-content').innerHTML = marked.parse(full);
    history.push({ role: 'assistant', content: full });

  } catch (err) {
    typingEl.classList.remove('typing');
    typingEl.querySelector('.md-content').textContent = `Sorry, something went wrong: ${err.message}`;
  } finally {
    setStreaming(false);
  }
}

// ── Helpers ───────────────────────────────────────────────────────────────────
function appendMessage(role, text, typing = false) {
  const div = document.createElement('div');
  div.className = `msg ${role}${typing ? ' typing' : ''}`;
  if (role === 'assistant') {
    const content = document.createElement('div');
    content.className = 'md-content';
    content.textContent = text;
    div.appendChild(content);
  } else {
    const p = document.createElement('p');
    p.textContent = text;
    div.appendChild(p);
  }
  messages.appendChild(div);
  scrollToBottom();
  return div;
}

function scrollToBottom() {
  messages.scrollTop = messages.scrollHeight;
}

function setStreaming(val) {
  isStreaming = val;
  sendBtn.disabled = val;
  input.disabled   = val;
}
