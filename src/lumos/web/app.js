// Lumos前端应用
// 单一文件，无构建步骤

const state = {
  accessToken: localStorage.getItem('lumos.access_token'),
  refreshToken: localStorage.getItem('lumos.refresh_token'),
  user: null,
  sessions: [],
  currentSession: null,
  ws: null,
  streamingMessage: null,
  skills: [],
  mcps: [],
  enabledSkills: new Set(),
};

const api = {
  async req(path, opts = {}) {
    const r = await fetch(path, {
      ...opts,
      headers: {
        'Content-Type': 'application/json',
        ...(opts.headers || {}),
        ...(state.accessToken ? { 'Authorization': `Bearer ${state.accessToken}` } : {}),
      },
    });
    if (r.status === 401 && state.refreshToken) {
      const refreshed = await this.refresh();
      if (refreshed) {
        return this.req(path, opts);
      } else {
        window.location.href = '/login';
      }
    }
    if (!r.ok) {
      const err = await r.json().catch(() => ({ detail: r.statusText }));
      throw new Error(typeof err.detail === 'string' ? err.detail : JSON.stringify(err.detail));
    }
    return r.status === 204 ? null : r.json();
  },
  async refresh() {
    const r = await fetch('/api/auth/refresh', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ refresh_token: state.refreshToken }),
    });
    if (!r.ok) return false;
    const data = await r.json();
    state.accessToken = data.access_token;
    state.refreshToken = data.refresh_token;
    localStorage.setItem('lumos.access_token', state.accessToken);
    localStorage.setItem('lumos.refresh_token', state.refreshToken);
    return true;
  },
};

// --- 认证 ---
async function checkAuth() {
  if (!state.accessToken) { window.location.href = '/login'; return; }
  try {
    state.user = await api.req('/api/auth/me');
    document.getElementById('user-email').textContent = state.user.email;
  } catch (e) {
    window.location.href = '/login';
  }
}

document.getElementById('btn-logout').onclick = async () => {
  try { await api.req('/api/auth/logout', { method: 'POST', body: JSON.stringify({ refresh_token: state.refreshToken }) }); } catch {}
  localStorage.clear();
  window.location.href = '/login';
};

// --- 会话列表 ---
async function loadSessions() {
  state.sessions = await api.req('/api/sessions');
  renderSessionList();
}

function renderSessionList() {
  const list = document.getElementById('session-list');
  list.innerHTML = '';
  for (const s of state.sessions) {
    const div = document.createElement('div');
    div.className = 'session-item' + (state.currentSession?.id === s.id ? ' active' : '');
    div.innerHTML = `
      <div>${escapeHtml(s.title)}</div>
      <div class="session-item-time">${new Date(s.updated_at).toLocaleString()}</div>
    `;
    div.onclick = () => selectSession(s.id);
    list.appendChild(div);
  }
}

async function selectSession(id) {
  state.currentSession = await api.req(`/api/sessions/${id}`);
  state.enabledSkills = new Set(state.currentSession.enabled_skills || []);
  renderSessionList();
  await loadMessages();
  connectWS(id);
}

document.getElementById('btn-new-session').onclick = async () => {
  const cs = await api.req('/api/sessions', { method: 'POST', body: JSON.stringify({}) });
  state.sessions.unshift(cs);
  await selectSession(cs.id);
};

async function loadMessages() {
  const msgs = await api.req(`/api/sessions/${state.currentSession.id}/messages`);
  const list = document.getElementById('messages');
  list.innerHTML = '';
  for (const m of msgs) {
    appendMessage(m);
  }
  list.scrollTop = list.scrollHeight;
}

function appendMessage(m) {
  const list = document.getElementById('messages');
  const div = document.createElement('div');
  div.className = `message ${m.role}`;
  const content = m.role === 'user' ? escapeHtml(m.content) : renderMarkdown(m.content);
  div.innerHTML = `
    <div class="message-role">${m.role}</div>
    <div class="message-content">${content}</div>
  `;
  list.appendChild(div);
  return div;
}

function renderMarkdown(text) {
  if (window.marked) {
    return window.marked.parse(text, { breaks: true });
  }
  return escapeHtml(text);
}

function escapeHtml(s) {
  return String(s)
    .replace(/&/g, '&amp;')
    .replace(/</g, '&lt;')
    .replace(/>/g, '&gt;')
    .replace(/"/g, '&quot;');
}

// --- WebSocket ---
function connectWS(sessionId) {
  if (state.ws) state.ws.close();
  const proto = location.protocol === 'https:' ? 'wss' : 'ws';
  const url = `${proto}://${location.host}/ws/sessions/${sessionId}?token=${state.accessToken}`;
  state.ws = new WebSocket(url);
  state.ws.onmessage = (e) => handleWsMessage(JSON.parse(e.data));
  state.ws.onclose = () => { state.ws = null; };
  state.ws.onerror = (e) => console.error('WS error', e);
}

function handleWsMessage(event) {
  const list = document.getElementById('messages');
  switch (event.type) {
    case 'text':
      if (!state.streamingMessage) {
        state.streamingMessage = { content: '', role: 'assistant' };
        const div = document.createElement('div');
        div.className = 'message assistant streaming';
        div.innerHTML = `<div class="message-role">assistant</div><div class="message-content"></div>`;
        list.appendChild(div);
        state.streamingMessage.el = div.querySelector('.message-content');
      }
      state.streamingMessage.content += event.data.delta;
      state.streamingMessage.el.innerHTML = renderMarkdown(state.streamingMessage.content);
      list.scrollTop = list.scrollHeight;
      break;
    case 'tool_call_start':
      appendToolCall(event.data.calls);
      break;
    case 'tool_call_result':
      updateToolCallResult(event.data);
      break;
    case 'tool_call_end':
      break;
    case 'usage':
      if (state.streamingMessage) {
        state.streamingMessage.usage = event.data;
      }
      break;
    case 'done':
      if (state.streamingMessage) {
        state.streamingMessage.el.classList.remove('streaming');
        const usageDiv = document.createElement('div');
        usageDiv.className = 'message-role';
        usageDiv.textContent = `📊 ${state.streamingMessage.usage?.prompt_tokens || 0} prompt / ${state.streamingMessage.usage?.completion_tokens || 0} completion tokens`;
        state.streamingMessage.el.parentElement.appendChild(usageDiv);
      }
      state.streamingMessage = null;
      loadSessions(); // 刷新列表（updated_at变化）
      break;
    case 'error':
      alert('Error: ' + (event.data?.message || JSON.stringify(event.data)));
      break;
    case 'cancelled':
      state.streamingMessage = null;
      break;
  }
}

function appendToolCall(calls) {
  const list = document.getElementById('messages');
  for (const tc of calls) {
    const div = document.createElement('div');
    div.className = 'tool-call expanded';
    div.dataset.toolId = tc.id;
    div.innerHTML = `
      <div class="tool-call-header">
        <span class="tool-call-name">🔧 ${tc.name}</span>
        <span class="tool-call-status running">运行中...</span>
      </div>
      <div class="tool-call-body">
        <strong>参数:</strong>
        <pre>${escapeHtml(JSON.stringify(tc.arguments, null, 2))}</pre>
        <div class="tool-call-result"></div>
      </div>
    `;
    div.querySelector('.tool-call-header').onclick = () => div.classList.toggle('expanded');
    list.appendChild(div);
  }
}

function updateToolCallResult(data) {
  const div = document.querySelector(`.tool-call[data-tool-id="${data.tool_call_id}"]`);
  if (!div) return;
  const status = div.querySelector('.tool-call-status');
  status.classList.remove('running');
  status.classList.add(data.is_error ? 'error' : 'success');
  status.textContent = data.is_error ? '✗ 失败' : '✓ 完成';
  const resultEl = div.querySelector('.tool-call-result');
  resultEl.innerHTML = `<strong>结果:</strong><pre>${escapeHtml(data.result).slice(0, 2000)}${data.result.length > 2000 ? '\n...(truncated)' : ''}</pre>`;
}

// --- 发送 ---
document.getElementById('btn-send').onclick = sendMessage;
document.getElementById('input-text').onkeydown = (e) => {
  if (e.key === 'Enter' && !e.shiftKey) {
    e.preventDefault();
    sendMessage();
  }
};

async function sendMessage() {
  const input = document.getElementById('input-text');
  const content = input.value.trim();
  if (!content || !state.currentSession || !state.ws) return;

  // 显示user消息
  appendMessage({ role: 'user', content });

  // 发送WS消息
  state.ws.send(JSON.stringify({
    type: 'user_message',
    content,
    enabled_skills: Array.from(state.enabledSkills),
  }));
  input.value = '';
  document.getElementById('btn-send').style.display = 'none';
  document.getElementById('btn-cancel').style.display = '';
}

document.getElementById('btn-cancel').onclick = () => {
  if (state.ws) state.ws.send(JSON.stringify({ type: 'cancel' }));
  document.getElementById('btn-send').style.display = '';
  document.getElementById('btn-cancel').style.display = 'none';
};

// --- Skills管理 ---
async function loadSkills() {
  state.skills = await api.req('/api/skills');
  renderSkills();
  renderComposerSkills();
}

function renderSkills() {
  const list = document.getElementById('skill-list');
  list.innerHTML = '';
  for (const s of state.skills) {
    const card = document.createElement('div');
    card.className = 'skill-card';
    card.innerHTML = `
      <div style="display:flex;justify-content:space-between">
        <strong>${escapeHtml(s.name)}</strong>
        <button onclick="toggleSkill('${s.name}', ${s.enabled})">${s.enabled ? '停用' : '启用'}</button>
      </div>
      <p style="color:var(--fg-dim);margin-top:4px">${escapeHtml(s.description)}</p>
    `;
    list.appendChild(card);
  }
}

function renderComposerSkills() {
  const wrap = document.getElementById('composer-skills');
  wrap.innerHTML = '';
  for (const s of state.skills) {
    if (!s.enabled) continue;
    const lbl = document.createElement('label');
    lbl.innerHTML = `
      <input type="checkbox" ${state.enabledSkills.has(s.name) ? 'checked' : ''} onchange="toggleComposerSkill('${s.name}', this.checked)" />
      ${escapeHtml(s.name)}
    `;
    wrap.appendChild(lbl);
  }
}

window.toggleComposerSkill = async (name, on) => {
  if (on) state.enabledSkills.add(name);
  else state.enabledSkills.delete(name);
  if (state.currentSession) {
    await api.req(`/api/sessions/${state.currentSession.id}`, {
      method: 'PATCH', body: JSON.stringify({ enabled_skills: Array.from(state.enabledSkills) }),
    });
  }
};

window.toggleSkill = async (name, currentEnabled) => {
  const endpoint = currentEnabled ? 'disable' : 'enable';
  await api.req(`/api/skills/${name}/${endpoint}`, { method: 'POST' });
  await loadSkills();
};

// --- MCP管理 ---
async function loadMcps() {
  state.mcps = await api.req('/api/mcp/servers');
  renderMcps();
}

function renderMcps() {
  const list = document.getElementById('mcp-list');
  list.innerHTML = '';
  for (const m of state.mcps) {
    const card = document.createElement('div');
    card.className = 'mcp-card';
    card.innerHTML = `
      <div style="display:flex;justify-content:space-between">
        <strong>${escapeHtml(m.name)}</strong>
        <button onclick="deleteMcp('${m.id}')">删除</button>
      </div>
      <p style="color:var(--fg-dim);margin-top:4px;font-size:12px">
        ${escapeHtml(m.config.transport)}
        ${m.config.command ? `· ${escapeHtml(m.config.command)}` : ''}
        ${m.config.url ? `· ${escapeHtml(m.config.url)}` : ''}
      </p>
    `;
    list.appendChild(card);
  }
}

document.getElementById('btn-add-mcp').onclick = async () => {
  const name = prompt('MCP服务器名称:');
  if (!name) return;
  const transport = prompt('传输类型 (stdio/sse/streamable_http):', 'stdio');
  let body = { name, transport };
  if (transport === 'stdio') {
    body.command = prompt('命令:', 'npx');
    body.args = (prompt('参数（空格分隔）:', '-y @modelcontextprotocol/server-filesystem ./data') || '').split(/\s+/);
  } else {
    body.url = prompt('URL:', 'https://mcp.example.com/sse');
  }
  await api.req('/api/mcp/servers', { method: 'POST', body: JSON.stringify(body) });
  await loadMcps();
};

window.deleteMcp = async (id) => {
  if (!confirm('删除此MCP服务器?')) return;
  await api.req(`/api/mcp/servers/${id}`, { method: 'DELETE' });
  await loadMcps();
};

// --- 抽屉 ---
const drawer = document.getElementById('drawer');
document.getElementById('btn-drawer').onclick = () => drawer.classList.add('open');
document.getElementById('btn-drawer-bottom').onclick = () => drawer.classList.add('open');
document.getElementById('btn-close-drawer').onclick = () => drawer.classList.remove('open');

// --- 初始化 ---
(async () => {
  await checkAuth();
  await loadSessions();
  await loadSkills();
  await loadMcps();
  if (state.sessions.length > 0) {
    await selectSession(state.sessions[0].id);
  } else {
    // 自动创建首个会话
    document.getElementById('btn-new-session').click();
  }
})();