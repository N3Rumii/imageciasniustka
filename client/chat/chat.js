/**
 * ciasniutka chat - E2E encrypted messenger
 * 
 * Crypto: X25519 ECDH + AES-256-GCM via Web Crypto API
 * Network: REST API + polling every 3 seconds
 * Server stores only ciphertext blobs - can't read messages
 */

//  Crypto 

const Crypto = {
  ALGORITHM: { name: 'X25519' },
  ENCRYPT_ALGO: { name: 'AES-GCM', length: 256 },

  /** Generate an X25519 keypair. Returns CryptoKeyPair. */
  async generateKeyPair() {
    return await crypto.subtle.generateKey(this.ALGORITHM, true, ['deriveBits']);
  },

  /** Export public key to base64 string. */
  async exportPublicKey(key) {
    const raw = await crypto.subtle.exportKey('raw', key);
    return btoa(String.fromCharCode(...new Uint8Array(raw)));
  },

  /** Export private key to base64 string (for backup). */
  async exportPrivateKey(key) {
    const jwk = await crypto.subtle.exportKey('jwk', key);
    return JSON.stringify(jwk);
  },

  /** Import public key from base64 string. */
  async importPublicKey(base64) {
    const raw = Uint8Array.from(atob(base64), c => c.charCodeAt(0));
    return await crypto.subtle.importKey('raw', raw, this.ALGORITHM, true, []);
  },

  /** Import private key from JWK JSON. */
  async importPrivateKey(jwkJson) {
    const jwk = JSON.parse(jwkJson);
    return await crypto.subtle.importKey('jwk', jwk, this.ALGORITHM, true, ['deriveBits']);
  },

  /** Derive AES key via ECDH. Extractable so we can cache it. */
  async deriveKey(privateKey, publicKey) {
    const bits = await crypto.subtle.deriveBits(
      { name: 'X25519', public: publicKey },
      privateKey,
      256
    );
    return await crypto.subtle.importKey(
      'raw', bits, { name: 'AES-GCM' }, true, ['encrypt', 'decrypt']
    );
  },

  /** Encrypt plaintext with AES-256-GCM. Returns { ciphertext, iv } as base64. */
  async encrypt(key, plaintext) {
    const iv = crypto.getRandomValues(new Uint8Array(12));
    const encoded = new TextEncoder().encode(plaintext);
    const ct = await crypto.subtle.encrypt(
      { name: 'AES-GCM', iv }, key, encoded
    );
    return {
      ciphertext: btoa(String.fromCharCode(...new Uint8Array(ct))),
      iv: btoa(String.fromCharCode(...iv))
    };
  },

  /** Decrypt ciphertext with AES-256-GCM. */
  async decrypt(key, ciphertextB64, ivB64) {
    const ct = Uint8Array.from(atob(ciphertextB64), c => c.charCodeAt(0));
    const iv = Uint8Array.from(atob(ivB64), c => c.charCodeAt(0));
    const raw = await crypto.subtle.decrypt(
      { name: 'AES-GCM', iv }, key, ct
    );
    return new TextDecoder().decode(raw);
  },

  /** Compute 8-char hex fingerprint from public key for verification. */
  async fingerprint(publicKeyB64) {
    const raw = Uint8Array.from(atob(publicKeyB64), c => c.charCodeAt(0));
    const hash = await crypto.subtle.digest('SHA-256', raw);
    const hex = Array.from(new Uint8Array(hash), b => b.toString(16).padStart(2, '0')).join('');
    return hex.slice(0, 8).toUpperCase();
  }
};

//  API 

const API = {
  _base: '/api/chat',
  _token: null,

  setToken(tok) { this._token = tok; },

  async _fetch(path, opts = {}) {
    const url = this._base + path;
    const headers = { 'Accept': 'application/json' };
    if (opts.body) headers['Content-Type'] = 'application/json';
    if (this._token) headers['Authorization'] = 'Token ' + this._token;
    const res = await fetch(url, { ...opts, headers });
    if (!res.ok) {
      const err = await res.json().catch(() => ({ description: res.statusText }));
      throw new Error(err.description || 'Request failed');
    }
    return res.json();
  },

  uploadKey(publicKeyB64) {
    return this._fetch('/keys/', {
      method: 'POST',
      body: JSON.stringify({ publicKey: publicKeyB64 })
    });
  },

  getPublicKey(userName) {
    return this._fetch('/keys/' + encodeURIComponent(userName));
  },

  sendMessage(recipient, text, roomName, fileTokens) {
    const body = { recipient, text: text || '' };
    if (roomName) body.roomName = roomName;
    if (fileTokens && fileTokens.length) body.fileTokens = fileTokens;
    return this._fetch('/messages/', {
      method: 'POST',
      body: JSON.stringify(body)
    });
  },

  getMessages(userName, sinceId, roomName) {
    let path = '/messages/' + encodeURIComponent(userName);
    const params = [];
    if (sinceId) params.push('since=' + sinceId);
    if (roomName) params.push('room=' + encodeURIComponent(roomName));
    if (params.length) path += '?' + params.join('&');
    return this._fetch(path);
  },

  getConversations() {
    return this._fetch('/conversations/');
  },

  async poll(since) {
    let path = '/poll/';
    if (since) path += '?since=' + encodeURIComponent(since);
    return this._fetch(path);
  }
};

//  State 

const State = {
  userName: null,
  authToken: null,
  keyPair: null,        // CryptoKeyPair
  derivedKeys: {},      // userName -> CryptoKey (AES)
  activeConvo: null,    // userName of open conversation
  lastPoll: null,       // ISO timestamp

  async init() {
    // Read auth from URL fragment (passed by main site redirect)
    const hash = window.location.hash;
    if (hash && hash.startsWith('#token=')) {
      const token = hash.slice(7);
      API.setToken(token);
      // Decode to get username
      try {
        const decoded = atob(token);
        const [userName] = decoded.split(':');
        this.userName = userName;
        this.authToken = token;
        // Persist for future visits
        localStorage.setItem('chat_auth', JSON.stringify({ userName, token }));
        // Clean URL
        history.replaceState(null, '', window.location.pathname);
      } catch(e) { /* invalid token */ }
    }

    // Fall back to localStorage
    if (!this.authToken) {
      const stored = localStorage.getItem('chat_auth');
      if (stored) {
        const data = JSON.parse(stored);
        this.userName = data.userName;
        this.authToken = data.token;
        API.setToken(this.authToken);
      }
    }

    // Load or generate keypair (must survive page refreshes)
    try {
      const storedKey = localStorage.getItem('chat_privkey');
      if (storedKey) {
        const priv = await Crypto.importPrivateKey(storedKey);
        this.keyPair = { privateKey: priv, publicKey: null };
        const storedPub = localStorage.getItem('chat_pubkey');
        if (storedPub) {
          try {
            this.keyPair.publicKey = await Crypto.importPublicKey(storedPub);
          } catch(e) { /* public key corrupt, will re-derive from private */ }
        }
      }
    } catch(e) {
      // Key corrupt - will regenerate below
      console.warn('Chat key load failed, regenerating:', e.message);
      localStorage.removeItem('chat_privkey');
      localStorage.removeItem('chat_pubkey');
      localStorage.removeItem('chat_derived');
    }

    // Load cached derived AES keys
    try {
      const storedDerived = localStorage.getItem('chat_derived');
      if (storedDerived) {
        const raw = JSON.parse(storedDerived);
        for (const [name, jwk] of Object.entries(raw)) {
          try {
            this.derivedKeys[name] = await crypto.subtle.importKey(
              'jwk', jwk, { name: 'AES-GCM' }, false, ['encrypt', 'decrypt']
            );
          } catch(e) { /* skip corrupt entry */ }
        }
      }
    } catch(e) {
      localStorage.removeItem('chat_derived');
    }
  },

  async ensureKeys() {
    if (!this.keyPair) {
      this.keyPair = await Crypto.generateKeyPair();
      const pubB64 = await Crypto.exportPublicKey(this.keyPair.publicKey);
      const privJwk = await Crypto.exportPrivateKey(this.keyPair.privateKey);
      localStorage.setItem('chat_pubkey', pubB64);
      localStorage.setItem('chat_privkey', privJwk);
      await API.uploadKey(pubB64);
    }
  },

  cacheDerivedKey(userName, key) {
    this.derivedKeys[userName] = key;
    // Persist as JWK
    crypto.subtle.exportKey('jwk', key).then(jwk => {
      const stored = JSON.parse(localStorage.getItem('chat_derived') || '{}');
      stored[userName] = jwk;
      localStorage.setItem('chat_derived', JSON.stringify(stored));
    });
  }
};

//  UI 

const UI = {
  _convList: null,
  _msgList: null,
  _chatPane: null,
  _input: null,
  _pollTimer: null,

  init() {
    this._convList = document.getElementById('conversation-list');
    this._msgList = document.getElementById('message-list');
    this._chatPane = document.getElementById('chat-pane');
    this._input = document.getElementById('message-input');
    this._status = document.getElementById('status-bar');

    document.getElementById('send-btn').addEventListener('click', () => this._sendMessage());
    this._input.addEventListener('keydown', e => {
      if (e.key === 'Enter' && !e.shiftKey) { e.preventDefault(); this._sendMessage(); }
      this._autoResize();
    });
    this._input.addEventListener('input', () => this._autoResize());

    // File attachment
    this._pendingFiles = [];
    document.getElementById('attach-btn').addEventListener('click', () => {
      document.getElementById('file-input').click();
    });
    document.getElementById('file-input').addEventListener('change', () => {
      const input = document.getElementById('file-input');
      for (const f of input.files) this._addPendingFile(f);
      input.value = '';
    });

    // Mobile back button
    const chatHeader = document.getElementById('chat-header');
    const backBtn = document.createElement('button');
    backBtn.id = 'chat-back-btn';
    backBtn.textContent = 'Back';
    backBtn.style.cssText = 'display:none;background:none;border:none;color:#58a6ff;cursor:pointer;font-size:0.9em;padding:4px 8px;margin-right:8px';
    backBtn.addEventListener('click', () => this._goBack());
    chatHeader.insertBefore(backBtn, chatHeader.firstChild);
    // Show back button on mobile
    if (window.innerWidth <= 700) backBtn.style.display = '';

    // ... menu dropdown
    const menuBtn = document.getElementById('chat-menu-btn');
    const menuDD = document.getElementById('chat-menu-dropdown');
    if (menuBtn && menuDD) {
      menuBtn.addEventListener('click', e => {
        e.stopPropagation();
        menuDD.style.display = menuDD.style.display === 'none' ? '' : 'none';
      });
      menuDD.addEventListener('click', e => {
        const action = e.target.getAttribute('data-action');
        if (action === 'delete') this._deleteConversation();
        if (action === 'block') this._blockUser();
        if (action === 'encrypt') this.setStatus('E2E: coming soon');
        menuDD.style.display = 'none';
      });
      document.addEventListener('click', () => { menuDD.style.display = 'none'; });
    }

    // Room modal
    this._roomUsers = [];
    document.getElementById('new-room-btn').addEventListener('click', () => {
      this._roomUsers = [];
      this._renderRoomTags();
      document.getElementById('room-modal').style.display = 'flex';
      document.getElementById('room-users-input').focus();
    });
    document.getElementById('room-cancel-btn').addEventListener('click', () => {
      document.getElementById('room-modal').style.display = 'none';
    });
    document.getElementById('room-create-btn').addEventListener('click', () => {
      // Include any text left in the input
      const input = document.getElementById('room-users-input');
      if (input.value.trim()) {
        this._roomUsers.push(input.value.trim());
        input.value = '';
      }
      if (this._roomUsers.length) {
        this.openConversation(this._roomUsers[0], this._roomUsers.join(', '));
        document.getElementById('room-modal').style.display = 'none';
      }
    });
    // Room user input with auto-suggest
    const roomInput = document.getElementById('room-users-input');
    roomInput.addEventListener('input', () => this._suggestRoomUsers());
    roomInput.addEventListener('keydown', e => {
      if (e.key === 'Enter' || e.key === ',') {
        e.preventDefault();
        const name = roomInput.value.trim();
        if (name && !this._roomUsers.includes(name)) {
          this._roomUsers.push(name);
          this._renderRoomTags();
        }
        roomInput.value = '';
        this._hideRoomSuggestions();
      }
      if (e.key === 'Backspace' && !roomInput.value && this._roomUsers.length) {
        this._roomUsers.pop();
        this._renderRoomTags();
      }
    });
    document.addEventListener('click', e => {
      if (!e.target.closest('#room-modal') && !e.target.closest('#new-room-btn')) {
        document.getElementById('room-modal').style.display = 'none';
      }
    });

    // Key management panel
    this._buildKeyPanel();

    document.getElementById('new-convo-btn').addEventListener('click', () => {
      const name = document.getElementById('new-convo-input').value.trim();
      if (name) this.openConversation(name);
    });

    const newConvoInput = document.getElementById('new-convo-input');
    newConvoInput.addEventListener('keydown', e => {
      if (e.key === 'Enter') {
        const name = e.target.value.trim();
        if (name) this.openConversation(name);
      }
    });
    // Auto-suggest usernames
    newConvoInput.addEventListener('input', () => this._suggestUsers());
    document.addEventListener('click', e => {
      if (!e.target.closest('#new-convo') && !e.target.closest('.suggestions-dropdown')) {
        this._hideSuggestions();
      }
    });

  },

  async _suggestUsers() {
    const input = document.getElementById('new-convo-input');
    const query = input.value.trim();
    if (query.length < 1) { this._hideSuggestions(); return; }

    try {
      const res = await fetch('/api/users/?offset=0&limit=10&query=' + encodeURIComponent(query + '*'), {
        headers: { 'Accept': 'application/json', 'Authorization': 'Token ' + State.authToken }
      });
      if (!res.ok) return;
      const data = await res.json();
      const users = data.results || [];
      if (!users.length) { this._hideSuggestions(); return; }

      let dd = document.getElementById('suggestions-dropdown');
      if (!dd) {
        dd = document.createElement('div');
        dd.id = 'suggestions-dropdown';
        dd.style.cssText = 'position:absolute;background:#161b22;border:1px solid #30363d;border-radius:6px;max-height:200px;overflow-y:auto;z-index:100;width:100%;margin-top:4px';
        input.parentNode.style.position = 'relative';
        input.parentNode.appendChild(dd);
      }
      dd.innerHTML = '';
      for (const u of users) {
        if (u.name === State.userName) continue;
        const item = document.createElement('div');
        item.style.cssText = 'padding:8px 12px;cursor:pointer;font-size:0.9em;color:#c9d1d9';
        item.textContent = u.name;
        item.addEventListener('mousedown', e => { e.preventDefault(); input.value = u.name; this._hideSuggestions(); this.openConversation(u.name); });
        item.addEventListener('mouseenter', () => item.style.background = '#1c2128');
        item.addEventListener('mouseleave', () => item.style.background = '');
        dd.appendChild(item);
      }
    } catch(e) { /* silent */ }
  },

  _hideSuggestions() {
    const dd = document.getElementById('suggestions-dropdown');
    if (dd) dd.remove();
  },

  _renderRoomTags() {
    const container = document.getElementById('room-users-tags');
    container.innerHTML = '';
    for (const name of this._roomUsers) {
      const tag = document.createElement('span');
      tag.className = 'user-tag';
      tag.innerHTML = name + '<span class=\"remove-tag\" data-name=\"' + name + '\">x</span>';
      tag.querySelector('.remove-tag').addEventListener('click', () => {
        this._roomUsers = this._roomUsers.filter(n => n !== name);
        this._renderRoomTags();
      });
      container.appendChild(tag);
    }
  },

  async _suggestRoomUsers() {
    const input = document.getElementById('room-users-input');
    const query = input.value.trim();
    if (query.length < 1) { this._hideRoomSuggestions(); return; }

    try {
      const res = await fetch('/api/users/?offset=0&limit=8&query=' + encodeURIComponent(query + '*'), {
        headers: { 'Accept': 'application/json', 'Authorization': 'Token ' + State.authToken }
      });
      if (!res.ok) return;
      const data = await res.json();
      const users = (data.results || []).filter(u => u.name !== State.userName && !this._roomUsers.includes(u.name));
      if (!users.length) { this._hideRoomSuggestions(); return; }

      let dd = document.getElementById('room-users-suggest');
      dd.innerHTML = '';
      dd.style.display = '';
      for (const u of users) {
        const item = document.createElement('div');
        item.style.cssText = 'padding:8px 12px;cursor:pointer;font-size:0.9em;color:#c9d1d9';
        item.textContent = u.name;
        item.addEventListener('mousedown', e => {
          e.preventDefault();
          if (!this._roomUsers.includes(u.name)) {
            this._roomUsers.push(u.name);
            this._renderRoomTags();
          }
          input.value = '';
          this._hideRoomSuggestions();
          input.focus();
        });
        item.addEventListener('mouseenter', () => item.style.background = '#1c2128');
        item.addEventListener('mouseleave', () => item.style.background = '');
        dd.appendChild(item);
      }
    } catch(e) { /* silent */ }
  },

  _hideRoomSuggestions() {
    const dd = document.getElementById('room-users-suggest');
    if (dd) { dd.innerHTML = ''; dd.style.display = 'none'; }
  },

  _addPendingFile(file) {
    this._pendingFiles.push(file);
    this._renderFilePreview();
  },

  _renderFilePreview() {
    const container = document.getElementById('upload-preview');
    container.style.display = this._pendingFiles.length ? 'flex' : 'none';
    container.innerHTML = '';
    for (let i = 0; i < this._pendingFiles.length; i++) {
      const f = this._pendingFiles[i];
      const div = document.createElement('div');
      div.className = 'upload-preview-item';
      if (f.type.startsWith('image/')) {
        const img = document.createElement('img');
        img.src = URL.createObjectURL(f);
        div.appendChild(img);
      } else {
        div.textContent = 'VID';
        div.style.cssText += 'display:flex;align-items:center;justify-content:center;color:#888;font-size:0.7em';
      }
      const rm = document.createElement('button');
      rm.className = 'remove-preview';
      rm.textContent = 'x';
      rm.addEventListener('click', () => {
        this._pendingFiles.splice(i, 1);
        this._renderFilePreview();
      });
      div.appendChild(rm);
      container.appendChild(div);
    }
  },

  async _uploadFile(file) {
    const token = API._token || State.authToken || '';
    const form = new FormData();
    form.append('content', file);
    const res = await fetch('/api/chat/upload/', {
      method: 'POST',
      headers: token ? { 'Authorization': 'Token ' + token } : {},
      body: form
    });
    if (!res.ok) {
      const err = await res.json().catch(() => ({ description: 'Upload failed' }));
      throw new Error(err.description || 'Upload failed (HTTP ' + res.status + ')');
    }
    const data = await res.json();
    return data.token;
  },

  _goBack() {
    State.activeConvo = null;
    this._chatPane.classList.add('empty');
    this.loadConversations();
  },

  _buildKeyPanel() {
    const sidebar = document.getElementById('sidebar');
    const panel = document.createElement('div');
    panel.id = 'key-panel';
    panel.innerHTML =
      '<details><summary style="color:#888;cursor:pointer;font-size:0.85em">Key Management</summary>' +
      '<button id="export-key-btn">Export Key</button> ' +
      '<button id="import-key-btn">Import Key</button>' +
      '<textarea id="key-textarea" placeholder="Paste exported key here..." style="display:none"></textarea>' +
      '<button id="key-apply-btn" style="display:none">Apply</button>' +
      '<div id="key-status" style="color:#58a6ff;margin-top:4px"></div>' +
      '</details>';
    sidebar.appendChild(panel);

    document.getElementById('export-key-btn').addEventListener('click', () => this._exportKey());
    document.getElementById('import-key-btn').addEventListener('click', () => {
      const ta = document.getElementById('key-textarea');
      const btn = document.getElementById('key-apply-btn');
      ta.style.display = ''; btn.style.display = '';
      ta.focus();
    });
    document.getElementById('key-apply-btn').addEventListener('click', () => this._importKey());
  },

  async _exportKey() {
    const privKey = localStorage.getItem('chat_privkey');
    if (!privKey) {
      document.getElementById('key-status').textContent = 'No key to export.';
      return;
    }
    // Package key + derived keys into a single transferable blob
    const bundle = {
      privkey: privKey,
      pubkey: localStorage.getItem('chat_pubkey') || '',
      derived: JSON.parse(localStorage.getItem('chat_derived') || '{}'),
      exportedAt: new Date().toISOString(),
    };
    const encoded = btoa(JSON.stringify(bundle));
    // Show in textarea for copy
    const ta = document.getElementById('key-textarea');
    ta.style.display = '';
    ta.value = encoded;
    ta.select();
    document.getElementById('key-status').textContent = 'Key copied! Paste this on your other device.';
    // Also try clipboard API
    try {
      await navigator.clipboard.writeText(encoded);
      document.getElementById('key-status').textContent = 'Key copied to clipboard! Paste on other device.';
    } catch(e) {}
  },

  async _importKey() {
    const encoded = document.getElementById('key-textarea').value.trim();
    if (!encoded) return;
    try {
      const bundle = JSON.parse(atob(encoded));
      if (!bundle.privkey) throw new Error('Invalid key bundle');
      localStorage.setItem('chat_privkey', bundle.privkey);
      if (bundle.pubkey) localStorage.setItem('chat_pubkey', bundle.pubkey);
      if (bundle.derived) localStorage.setItem('chat_derived', JSON.stringify(bundle.derived));
      document.getElementById('key-status').textContent = 'Key imported! Reloading...';
      setTimeout(() => location.reload(), 1000);
    } catch(e) {
      document.getElementById('key-status').textContent = 'Invalid key data.';
    }
  },

  async _deleteConversation() {
    if (!State.activeConvo) return;
    if (!confirm('Delete conversation with ' + State.activeConvo + '?')) return;
    try {
      await fetch('/api/chat/conversations/' + encodeURIComponent(State.activeConvo), {
        method: 'DELETE',
        headers: { 'Accept': 'application/json', 'Authorization': 'Token ' + State.authToken }
      });
      State.activeConvo = null;
      this._chatPane.classList.add('empty');
      this._msgList.innerHTML = '';
      // Remove derived key
      delete State.derivedKeys[State.activeConvo];
      this.loadConversations();
      this.setStatus('Conversation deleted');
    } catch(e) {
      this.setStatus('' + e.message);
    }
  },

  _blockUser() {
    if (!State.activeConvo) return;
    if (!confirm('Block ' + State.activeConvo + '? They won\'t be able to message you.')) return;

    // Call the real block API
    const token = State.authToken || '';
    fetch('/api/user/' + encodeURIComponent(State.activeConvo) + '/block/', {
      method: 'POST',
      headers: token ? { 'Authorization': 'Token ' + token, 'Accept': 'application/json' } : { 'Accept': 'application/json' },
    }).catch(() => { /* best-effort */ });

    // Also keep local cache
    const blocked = JSON.parse(localStorage.getItem('chat_blocked') || '[]');
    if (!blocked.includes(State.activeConvo)) {
      blocked.push(State.activeConvo);
      localStorage.setItem('chat_blocked', JSON.stringify(blocked));
    }
    this._deleteConversation();
    this.setStatus('Blocked: ' + State.activeConvo);
  },

  _autoResize() {
    this._input.style.height = 'auto';
    this._input.style.height = Math.min(this._input.scrollHeight, 100) + 'px';
  },

  setStatus(text) {
    this._status.textContent = text;
  },

  /** Load conversation list from server. */
  async loadConversations() {
    try {
      const data = await API.getConversations();
      this._convList.innerHTML = '';
      for (const c of data.results) {
        const el = document.createElement('div');
        el.className = 'conversation-item';
        const displayName = c.name || c.otherUser.name;
        el.innerHTML =
          '<div class="conversation-avatar">' +
          (c.otherUser.avatarUrl ? `<img src="${this._esc(c.otherUser.avatarUrl)}" alt="">` : '') +
          '</div>' +
          '<div>' +
          `<div class="conversation-name">${this._esc(displayName)}</div>` +
          `<div class="conversation-preview">${c.type === 'room' ? 'Room' : 'Encrypted'}</div>` +
          '</div>';
        const convoTarget = c.type === 'room' && c.name ? c.name : c.otherUser.name;
        const convoDisplay = c.name || c.otherUser.name;
        el.addEventListener('click', () => this.openConversation(convoTarget, convoDisplay, c.type));
        this._convList.appendChild(el);
      }
    } catch(e) {
      this.setStatus('' + e.message);
    }
  },

  /** Open a conversation with a user. */
  async openConversation(userName, displayName, convoType) {
    if (!State.userName) {
      this.setStatus('Login required - go to ciasniutka.pl first');
      return;
    }
    State.activeConvo = userName;
    State.activeConvoType = convoType || 'dm';
    State.activeRoomName = convoType === 'room' ? (displayName || userName) : null;
    this._chatPane.classList.remove('empty');
    document.getElementById('chat-username').textContent = displayName || userName;
    document.getElementById('new-convo-input').value = '';
    // Show back button on mobile
    const backBtn = document.getElementById('chat-back-btn');
    if (backBtn && window.innerWidth <= 700) backBtn.style.display = '';

    // Load messages
    this._msgList.innerHTML = '<div style="text-align:center;color:#484f58;padding:20px">Loading messages...</div>';
    try {
      const data = await API.getMessages(userName, null, State.activeRoomName);
      this._msgList.innerHTML = '';
      for (const m of data.results) {
        await this._renderMessage(m);
      }
      this._scrollBottom();
    } catch(e) {
      this._msgList.innerHTML = '<div style="text-align:center;color:#f85149;padding:20px">Error: ' + this._esc(e.message) + '</div>';
    }

    // Load fingerprint
    try {
      const keyData = await API.getPublicKey(userName);
      if (keyData && keyData.publicKey) {
        const fp = await Crypto.fingerprint(keyData.publicKey);
        document.getElementById('chat-fingerprint').textContent = '' + fp;
      } else {
        document.getElementById('chat-fingerprint').textContent = 'No key';
      }
    } catch(e) {
      document.getElementById('chat-fingerprint').textContent = '';
    }

    // Ensure we have a derived key
    if (!State.derivedKeys[userName]) {
      try {
        const key = await this._deriveKeyFor(userName);
        if (key) {
          // Flush any queued messages for this user
          await this._flushQueue(userName);
        }
      } catch(e) {
        this.setStatus('Key exchange failed: ' + e.message);
      }
    }

    // Highlight active
    for (const el of this._convList.querySelectorAll('.conversation-item')) {
      el.classList.toggle('active', el.querySelector('.conversation-name')?.textContent === userName);
    }

    this._input.focus();
  },

  async _deriveKeyFor(userName) {
    await State.ensureKeys();
    const keyData = await API.getPublicKey(userName);
    if (!keyData || !keyData.publicKey) {
      // Other user has no key yet - conversation works but messages are queued
      this.setStatus('' + userName + ' has no encryption key yet. Messages will send when they generate one.');
      return null;
    }
    const theirPub = await Crypto.importPublicKey(keyData.publicKey);
    const aesKey = await Crypto.deriveKey(State.keyPair.privateKey, theirPub);
    State.cacheDerivedKey(userName, aesKey);
    return aesKey;
  },

  async _renderMessage(m) {
    const isSent = m.senderName === State.userName;
    const div = document.createElement('div');
    div.className = 'message ' + (isSent ? 'sent' : 'received');
    div.setAttribute('data-id', m.id);

    if (m.text) {
      const t = document.createElement('div');
      t.textContent = m.text;
      div.appendChild(t);
    }
    if (m.post) {
      const url = m.post.contentUrl || m.post.avifUrl || m.post.av1Url;
      if (m.post.type === 'image' || m.post.type === 'animation') {
        const img = document.createElement('img');
        img.className = 'message-image';
        img.src = url;
        img.addEventListener('click', () => window.open(url, '_blank'));
        div.appendChild(img);
      } else if (m.post.type === 'video') {
        const vid = document.createElement('video');
        vid.className = 'message-video';
        vid.controls = true;
        vid.src = url;
        div.appendChild(vid);
      }
    }

    const time = document.createElement('div');
    time.className = 'message-time';
    const d = new Date(m.createdAt);
    time.textContent = d.toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' });
    div.appendChild(time);

    this._msgList.appendChild(div);
  },

  async _sendMessage() {
    const text = this._input.value.trim();
    const files = [...this._pendingFiles];
    if (!text && !files.length) return;
    if (!State.activeConvo) return;

    this._input.value = '';
    this._pendingFiles = [];
    this._renderFilePreview();
    this._autoResize();
    document.getElementById('send-btn').disabled = true;

    // Upload files first
    const fileTokens = [];
    for (const f of files) {
      try {
        this.setStatus('Uploading ' + f.name + '...');
        const token = await this._uploadFile(f);
        if (token) fileTokens.push(token);
      } catch(e) {
        this.setStatus('Upload failed: ' + e.message);
        document.getElementById('send-btn').disabled = false;
        return;
      }
    }

    // Send the message
    try {
      await API.sendMessage(State.activeConvo, text || '', State.activeRoomName, fileTokens.length ? fileTokens : null);
      this._renderSent(text || '', files);
      this._scrollBottom();
      this.loadConversations();
      this.setStatus('');
    } catch(e) {
      this.setStatus('Send failed: ' + e.message);
    }
    document.getElementById('send-btn').disabled = false;
    this._input.focus();
  },

  _queueMessage(userName, text) {
    const queue = JSON.parse(localStorage.getItem('chat_queue_' + userName) || '[]');
    queue.push({ text, time: new Date().toISOString() });
    localStorage.setItem('chat_queue_' + userName, JSON.stringify(queue));
  },

  async _flushQueue(userName) {
    const queue = JSON.parse(localStorage.getItem('chat_queue_' + userName) || '[]');
    if (!queue.length) return;
    const key = State.derivedKeys[userName];
    if (!key) return;

    for (const item of queue) {
      try {
        const { ciphertext, iv } = await Crypto.encrypt(key, item.text);
        await API.sendMessage(userName, ciphertext, iv);
      } catch(e) {
        // keep in queue
        return;
      }
    }
    localStorage.removeItem('chat_queue_' + userName);
    this.setStatus('Queued messages sent to ' + userName);
  },

  _renderSent(text, files) {
    const div = document.createElement('div');
    div.className = 'message sent';
    if (text) {
      const t = document.createElement('div');
      t.textContent = text;
      div.appendChild(t);
    }
    if (files && files.length) {
      for (const f of files) {
        if (f.type.startsWith('image/')) {
          const img = document.createElement('img');
          img.className = 'message-image';
          img.src = URL.createObjectURL(f);
          div.appendChild(img);
        } else if (f.type.startsWith('video/')) {
          const vid = document.createElement('video');
          vid.className = 'message-video';
          vid.controls = true;
          vid.src = URL.createObjectURL(f);
          div.appendChild(vid);
        }
      }
    }
    const time = document.createElement('div');
    time.className = 'message-time';
    time.textContent = new Date().toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' });
    div.appendChild(time);
    this._msgList.appendChild(div);
  },

  _scrollBottom() {
    this._msgList.scrollTop = this._msgList.scrollHeight;
  },

  _esc(s) {
    const d = document.createElement('div');
    d.textContent = s;
    return d.innerHTML;
  },

  /** Poll for new messages every 3 seconds. */
  async _pollLoop() {
    try {
      const data = await API.poll(State.lastPoll);
      State.lastPoll = data.serverTime || new Date().toISOString();
      for (const m of data.results || []) {
        // If we're viewing this conversation, render it
        if (State.activeConvo && m.senderName === State.activeConvo) {
          await this._renderMessage(m);
          this._scrollBottom();
        }
        // Refresh conversation list for ordering
        this.loadConversations();
      }
    } catch(e) { /* silent */ }
    this._pollTimer = setTimeout(() => this._pollLoop(), 3000);
  },

  startPolling() {
    this._pollLoop();
  }
};

//  Boot 

(async function() {
  await State.init();

  if (!State.userName) {
    // Not logged in - show prompt
    document.getElementById('empty-state').innerHTML =
      '<div class="empty-icon"></div>' +
      '<p>Login required</p>' +
      '<p style="font-size:0.85em;margin-top:8px"><a href="https://ciasniutka.pl" style="color:#58a6ff">Go to ciasniutka.pl</a> to sign in, then return here.</p>';
    document.getElementById('message-composer').style.display = 'none';
    return;
  }

  UI.init();
  await State.ensureKeys();
  UI.setStatus('E2E ready • ' + State.userName);
  await UI.loadConversations();
  UI.startPolling();
})();
