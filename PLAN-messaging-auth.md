# Messaging System + Auth Hardening — Implementation Plan

## Phase 0 — Secure Logging & Authentik Migration

### 0.1 Sanitize Request Logging

**Current state**: `request_logger.py` logs `user.name` and query count per
request. `posts.py`, `images.py`, `audio.py`, `tagger.py` log with debug context
but no structured format, making log scanning noisy.

**Changes**:

- **`server/szurubooru/middleware/request_logger.py`** — Replace `logger.info`
  with structured JSON log lines. Strip PII: hash user names, never log tokens
  or passwords, redact `Authorization` header values. Add request latency.
- **`server/szurubooru/rest/app.py`** — Catch unhandled exceptions and log them
  as structured JSON with traceback, but redact request body fields that look
  like secrets (`password`, `token`, `secret`).
- **`server/szurubooru/func/posts.py`** — Reduce log volume (many `logger.info`
  calls per conversion). Switch to `logger.debug` for per-post details, keep
  `logger.info` only for batch-level summaries.
- **Audit all `logger.warning`/`logger.exception` calls** across `func/` —
  ensure no secrets in exception messages or stack context.

### 0.2 Authentik OIDC Integration

**Why Authentik?** Centralized identity, MFA support, no local password storage,
automatic user provisioning, group→rank mapping.

**Architecture**:

```
Browser → Authentik (OIDC login) → szurubooru (validates JWT)
                                        │
                                        ├─ JIT user provisioning (first login)
                                        ├─ Group → rank mapping
                                        └─ Legacy token auth retained for API clients
```

**New files**:

| File | Purpose |
|------|---------|
| `server/szurubooru/auth/oidc.py` | OIDC client: JWT validation, JWKS fetch, userinfo |
| `server/szurubooru/auth/authentik.py` | Authentik-specific: group→rank mapping, JIT provisioning |
| `server/szurubooru/api/auth_api.py` | OIDC callback endpoint, login URL redirect |
| `server/szurubooru/tests/auth/test_oidc.py` | Tests |
| `server/szurubooru/migrations/versions/XXXX_oidc_fields.py` | Add `oidc_sub`, `oidc_iss` columns to user table |

**Modified files**:

| File | Change |
|------|--------|
| `server/szurubooru/middleware/authenticator.py` | Accept `Bearer <JWT>` in addition to `Basic` and `Token`. Validate JWT via OIDC JWKS. |
| `server/szurubooru/model/user.py` | Add `oidc_sub` (subject), `oidc_iss` (issuer) columns |
| `server/szurubooru/func/users.py` | Add `create_user_from_oidc()` — JIT provisioning on first Authentik login |
| `server/config.yaml.dist` | Add `oidc` block: issuer URL, client ID, client secret, group→rank map |
| `server/requirements.txt` | Add `python-jose[cryptography]` for JWT validation, `httpx` for JWKS fetch |
| `docker-compose.yml` | Add `authentik-server` and `authentik-worker` services |

**Group → rank mapping** (in config.yaml):

```yaml
oidc:
  issuer: https://auth.example.com/application/o/szurubooru/
  client_id: "..."
  client_secret: "..."
  group_rank_map:
    szuru-admins: administrator
    szuru-moderators: moderator
    szuru-power: power
    szuru-users: regular
  default_rank: restricted
```

**Auth flow**:

1. User visits `/api/auth/login` → redirect to Authentik OIDC authorize
2. Authentik callback → `/api/auth/callback` → exchange code for tokens
3. Validate ID token JWT, extract `sub` + `iss`
4. Look up user by `oidc_sub`+`oidc_iss` → existing user: log in
5. New user: JIT provision → create `model.User` with mapped rank
6. Issue szurubooru API token (for existing token-auth clients) + set session cookie

**Legacy compat**: Keep `Basic` and `Token` auth working alongside OIDC so
existing API scripts don't break. Add `POST /api/user-token/{user}` endpoint
so OIDC-authenticated users can generate API tokens for scripts.

### 0.3 About the Mail Subdomain

**Yes, register a mail subdomain** (e.g., `mail.example.com` or use an external
service). Authentik needs to send:

- Account verification emails
- Password reset emails
- MFA enrollment confirmations
- Welcome / invite emails

Options:

- **Easiest**: Point Authentik's SMTP config at a transactional email service
  (SendGrid, Mailgun, SES, Postmark). No subdomain needed — they handle DKIM/SPF.
- **Self-hosted**: Use the existing SMTP block in `server/config.yaml` (already
  present for szurubooru's password-reset emails) and point Authentik at it too.
  A subdomain like `mail.example.com` with proper SPF/DKIM/DMARC records avoids
  the spam folder.

Recommendation: use a transactional email service for deliverability. If you
want to keep it self-hosted, register `mail.<your-domain>` and set up SPF +
DKIM.

---

## Phase 1 — E2E Messaging System

### 1.1 Database Models + Migration

**New file: `server/szurubooru/model/message.py`**

```python
# Conversation — a group DM or 1:1 chat
class Conversation(Base):
    conversation_id = UUID, PK
    created_at, is_group, name (nullable)

# ConversationMember — join table with per-member state
class ConversationMember(Base):
    conversation_id → FK
    user_id → FK
    joined_at, left_at, last_read_at

# Message — ciphertext blob, server never decrypts
class Message(Base):
    message_id = UUID, PK
    conversation_id → FK
    sender_id → FK (user)
    ciphertext = BYTEA (XChaCha20-Poly1305 encrypted)
    nonce = BYTEA (24 bytes)
    sender_public_key = BYTEA (32 bytes, X25519)
    created_at

# MessageAttachment — encrypted file blob
class MessageAttachment(Base):
    attachment_id = UUID, PK
    message_id → FK
    ciphertext_path = VARCHAR (filesystem path)
    nonce, encryption_key_ciphertext (wrapped with conversation key)
    mime_type, original_size, compressed_size

# PublicKeyRegistry — user public keys for E2E
class PublicKeyRegistry(Base):
    user_id → FK (unique per device)
    device_id = VARCHAR
    public_key = BYTEA (X25519, 32 bytes)
    signed_pre_key = BYTEA (signed by user's main key)
    created_at, last_updated
```

Alembic migration auto-generated, placed in
`server/szurubooru/migrations/versions/`.

### 1.2 Config + Privileges

Add to `server/config.yaml.dist`:

```yaml
messaging:
  tcp_port: 8765        # WS/TCP server port
  max_message_size: 1048576  # 1 MiB max ciphertext
  attachment_max_size: 52428800  # 50 MiB

privileges:
  'messages:send':        regular
  'messages:list':        regular
  'messages:view':        regular
  'messages:delete:any':  moderator
  'messages:delete:own':  regular
  'conversations:create': regular
  'conversations:list':   regular
```

### 1.3 Business Logic

**New file: `server/szurubooru/func/messages.py`**

- `create_conversation(creator, member_ids, name, is_group)` — create + add members
- `send_message(conversation_id, sender, ciphertext, nonce, sender_pk)` — store ciphertext, notify via WS
- `get_messages(conversation_id, user, before, limit)` — paginated history (ciphertexts only)
- `get_conversations(user)` — list user's conversations with last message preview
- `register_public_key(user, device_id, public_key, signed_pre_key)` — key registry
- `get_public_keys(user_ids)` — batch fetch for handshake initiation
- `delete_message(message_id, user)` — soft-delete, privilege-checked
- `mark_read(conversation_id, user)` — update last_read_at

All functions run `auth.verify_privilege()` checks.

### 1.4 REST API Endpoints

**New file: `server/szurubooru/api/message_api.py`**

| Method | Path | Handler |
|--------|------|---------|
| `GET` | `/api/conversations` | List user's conversations |
| `POST` | `/api/conversations` | Create new conversation |
| `GET` | `/api/conversation/(\d+)` | Get conversation metadata |
| `PUT` | `/api/conversation/(\d+)` | Update (name, add/remove members) |
| `DELETE` | `/api/conversation/(\d+)` | Leave/delete conversation |
| `GET` | `/api/conversation/(\d+)/messages` | Paginated message history |
| `POST` | `/api/conversation/(\d+)/messages` | Send encrypted message |
| `DELETE` | `/api/message/(\d+)` | Delete own message |
| `POST` | `/api/keys` | Register public key |
| `GET` | `/api/keys/(\d+)` | Get user's public keys |
| `POST` | `/api/attachment` | Upload encrypted attachment chunk |

Registered via `@routes.get/post/put/delete` decorators, consistent with
existing API pattern.

### 1.5 Real-Time TCP/WS Server

**New file: `server/szurubooru/messaging/server.py`**

Standalone asyncio process (started separately from WSGI). Uses Python's
`asyncio` + `websockets` library.

**Protocol**: One JSON object per line, `\n`-delimited. No multiplexing
framing, no sub-protocol negotiation.

**Message types**:

| Type | Direction | Purpose |
|------|-----------|---------|
| `auth` | client→server | Authenticate with szurubooru API token |
| `subscribe` | client→server | Subscribe to conversation updates |
| `message` | server→client | New message notification (ciphertext relayed) |
| `presence` | server→client | User came online / went offline |
| `typing` | client↔server | Typing indicator relay |
| `ack` | client→server | Acknowledge receipt (server marks delivered) |

Server validates auth token on connect, tracks active connections per user,
relays messages to all online conversation members. Offline messages are
fetched via REST on reconnect.

**Docker**: New container `messaging` in `docker-compose.yml`, environment
variable `MESSAGING_PORT`.

### 1.6 Server Tests

- `server/szurubooru/tests/func/test_messages.py` — unit tests for business logic
- `server/szurubooru/tests/api/test_message_api.py` — integration tests for endpoints
- `server/szurubooru/tests/messaging/test_server.py` — WS server test client

Run via existing `scripts/run-server-tests.sh` (pytest -n auto in Docker).

---

## Phase 2 — Client-Side E2E + UI

### 2.1 E2E Encryption Module

**New file: `client/js/crypto/e2e.js`**

Depends on `tweetnacl` (already available via npm — 3 KiB gzipped, pure JS,
no WASM). Wraps:

- **Key generation**: `nacl.box.keyPair()` → X25519 keypair, stored in IndexedDB
- **Encrypt**: `encrypt(plaintext, recipientPublicKey, senderSecretKey)` →
  XChaCha20-Poly1305 (via `nacl.secretbox` after shared key derivation)
- **Decrypt**: `decrypt(ciphertext, nonce, senderPublicKey, recipientSecretKey)`
- **X3DH handshake**: Exchange pre-keys via server, derive shared secret
- **Attachment encrypt**: Chunked (1 MiB), each chunk gets derived nonce via
  HKDF-SHA256. Returns array of `{ciphertext, nonce, chunkIndex}`.
- **Ratchet**: Double Ratchet for forward secrecy — each message advances the
  chain key. Old keys deleted after use.

Key exchange flow:

```
Alice                           Server                          Bob
  │                               │                               │
  │── POST /api/keys (pk_A) ──────│                               │
  │                               │── GET /api/keys/alice ────────│
  │                               │   (Bob fetches pk_A)          │
  │                               │                               │
  │── Alice encrypts with pk_B ───│── ciphertext relay ───────────│
  │   (derived from handshake)    │   (server can't read)         │
```

### 2.2 Media Encoding (Client-Side)

**New file: `client/js/crypto/media.js`**

- **Images → AVIF**: Use `<canvas>` + `OffscreenCanvas` to decode, then encode
  via browser's built-in WebP (fallback) or Squoosh WASM AVIF encoder. Resize
  to max 2048px on longest edge before encode.
- **Audio → Opus**: Use `MediaRecorder` API with `audio/webm;codecs=opus` for
  recordings. For uploaded files, use `AudioContext.decodeAudioData()` then
  re-encode via `MediaRecorder` at 64 kbps.
- **Video → AV1**: `MediaRecorder` with AV1 if available, else VP9 fallback.
- All encoding happens BEFORE encryption — ciphertext is already minimal.

### 2.3 Messaging Client Service

**New file: `client/js/messaging_client.js`**

- Connects to WS server on page load (after auth)
- Maintains reconnect with exponential backoff (1s → 30s max)
- Message queue: outgoing messages queued when offline, sent on reconnect
- Incoming: decrypts → dispatches to UI via existing `events.EventTarget` pattern
- Pre-fetches conversation list via REST on init
- Typing indicator: throttled at 2s, sends `{"type":"typing","conversation_id":"..."}`

### 2.4 Messaging UI (MVC)

Following existing patterns in `client/js/`:

**Models**:

- `client/js/models/conversation.js` — conversation data + member list
- `client/js/models/message.js` — message data + decrypted content cache

**Views**:

- `client/js/views/conversations_list_view.js` — left panel: conversation list
  with avatars, last message preview, unread badge
- `client/js/views/chat_view.js` — right panel: message bubbles, date dividers,
  attachment thumbnails, typing indicator, message input bar

**Controllers**:

- `client/js/controllers/messages_controller.js` — orchestrates conversation
  list + chat view, handles navigation, keyboard shortcuts

**Templates**:

- `client/html/messages.tpl` — main messaging layout (split panel)
- `client/html/chat.tpl` — chat view template
- `client/html/conversation_row.tpl` — single conversation in list

**Styles**:

- `client/css/messages.styl` — layout: flexbox split panel, message bubbles
  (sent right-aligned, received left-aligned), attachment cards, unread dots.
  Font: existing Open Sans. Colors: using existing CSS variables from
  `core-general.styl`.

Layout wireframe:

```
┌──────────────────────┬──────────────────────────────────┐
│  Messages  🔍 [new] │  Chat with UserName              │
│                      │                                  │
│  ┌─────────────────┐ │  ┌────────────────────────────┐ │
│  │ User A  ✓seen   │ │  │          Hello!       ✓✓  │ │
│  │ "last msg..."   │ │  └────────────────────────────┘ │
│  └─────────────────┘ │       ┌────────────────────────┐ │
│  ┌─────────────────┐ │       │ Hey! How are you?      │ │
│  │ User B  ● unread│ │       └────────────────────────┘ │
│  │ "check this..." │ │                                  │
│  └─────────────────┘ │  ┌────┐ ┌────┐ ┌──────────────┐ │
│                      │  │ 📷 │ │ 🎵 │ │ 📎 attachment│ │
│                      │  └────┘ └────┘ └──────────────┘ │
│                      │                                  │
│                      │  ✎ Type a message...       [▶]  │
└──────────────────────┴──────────────────────────────────┘
```

### 2.5 Integration with Build Pipeline

No new build step needed. New JS files are `require()`-ed from controllers
which are already wired into Browserify via `client/js/main.js`. New Stylus
files are `@import`-ed from existing CSS. Templates go in `client/html/`.

### 2.6 Anti-Spy Hardening Checklist

- [x] Private keys in IndexedDB, never sent to server
- [x] Messages encrypted before leaving `e2e.js`, decrypted after arriving
- [x] Server stores only `ciphertext` + `nonce` + `sender_public_key` — no
  plaintext, no shared secrets
- [x] Attachment file names are random UUIDs, not original names
- [x] Per-message random nonces (no nonce reuse)
- [x] Double Ratchet for forward secrecy (old keys deleted)
- [x] Log sanitization from Phase 0 ensures ciphertext doesn't leak to logs
- [x] Authentik MFA protects account takeover
- [x] No message content in HTTP access logs (only endpoint paths)
- [ ] Optional self-destruct timers (future)
- [ ] Optional screenshot detection (future, requires native app)
