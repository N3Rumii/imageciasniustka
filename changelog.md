# ciasniutka changelog

## 2026-07-14 — Chat media attachments

### Added
- File attachment button (`+`) in chat composer
- Image and video uploads to chat messages
- Uploaded files create linked Posts, converted to AVIF/AV1 in background
- Files larger than 4000px auto-resized to max 2000px before upload
- Inline image/video display in chat messages
- File preview thumbnails with remove button before sending
- Upload progress status messages

### Changed
- `chat_message` table: added `post_id` column
- `conversation` table: added `name` and `convo_type` columns
- Conversations now separated into DMs (type=dm) and Rooms (type=room)
- Room creation uses tag-style user input with auto-suggest
- Delete/Block/Encrypt buttons moved to `...` dropdown menu in chat header

### Fixed
- Room and DM conversations no longer collide (separate unique constraints)
- Server-side encryption now uses stdlib-only SHAKE-256 (no C deps needed)
- Message timestamps include `Z` suffix for correct timezone display
- Post unprivate bug: emptying whitelist no longer auto-adds uploader

### Known issues
- Chat messages sometimes fail to send (under investigation)
- Emojis stripped from chat UI per user request
- Pressing phone back button redirects to chat.ciasniutka.pl (unused subdomain)
- CSS collisions across pages causing layout shifts
- Community tab layout needs mobile optimization
- Blog posts layout broken on mobile
- Bulk upload tag input missing auto-complete
- Whitelist user input missing tag-style auto-complete
- No user blocking system (posts, community, messages)
- Dark mode not set as default

### TODO
- [ ] Fix chat message send failures
- [ ] Fix phone back button redirect (chat.ciasniutka.pl)
- [ ] Bulk upload: add tag auto-complete during multi-file upload
- [ ] Whitelist: tag-style user input with auto-complete (like room creation)
- [ ] User blocking system: block posts, community posts, messages
- [ ] User unblocking: manage blocked users list
- [ ] Dark mode as default theme
- [ ] CSS collision audit: fix layout breaks across all pages
- [ ] Community tab: better mobile layout
- [ ] Blog posts: better mobile layout
- [ ] Chat: fix chat.ciasniutka.pl subdomain DNS/tunnel routing

---

## 2026-07-13 — Bug fixes & polish

### Fixed
- Status spam prevention: same user + same text within 60s rejected
- Post delete version mismatch: retries with fresh version on conflict
- Snapshot batch insert crash: wrapped in try/except
- CSS sanitizer case-sensitivity bypass in user profiles
- Community tab: increased preload limit from 4 to 25, parent-only counting
- Tab/sort clicks now properly reset timeline instead of appending
- pyheif CFFI crash: replaced with ffmpeg HEIF decoder
- Notification bell now auto-polls on page load, login, and every 10 minutes

### Added
- Chat messages create notifications (`new_message` type)
- Notification bell auto-updates without manual clicking

---

## 2026-07-13 — E2E Encrypted Messenger

### Added
- Standalone chat SPA at `/chat/` (served on `ciasniutka.pl/chat/`)
- Cloudflare DNS `chat.ciasniutka.pl` configured
- Three DB tables: `user_key`, `conversation`, `chat_message`
- REST API: key upload, message send/receive, conversation list, polling
- Server-side encryption: SHAKE-256 stream cipher + HMAC (stdlib-only)
- Web Crypto API integration (X25519 + AES-256-GCM) on client
- Mobile-responsive layout with back button
- Auto-suggest usernames when starting conversations
- Room creation with tag-style multi-user input

### Changed
- Messages link added to main site top navigation
- Chat redirect controller passes auth token via URL hash

---

## 2026-07-13 — Music uploads + player

### Added
- Audio upload support (mp3, wav, flac, ogg, m4a) via existing upload pipeline
- Auto-conversion to Opus (96kbps) in background, original deleted
- Duration extraction via ffprobe
- Cover art extraction from audio metadata
- HTML5 audio player on post pages
- Metadata auto-population: title and artist from file ID3 tags
- Admin-only privilege gate (`tracks:view: administrator`)
- `type:audio` and `type:music` search filters
- `audio/opus` MIME type in nginx

### Changed
- Post model: added `TYPE_AUDIO`
- 8 new files created, 14 existing files modified

---

## 2026-07-07 — Security hardening

### Added
- CSP, X-Frame-Options, X-Content-Type-Options, HSTS, Referrer-Policy headers in nginx
- Rate limiting zones defined (not yet enabled)
- CSS sanitizer regex fix documented

### Changed
- Relaxed CSP to allow `https:` sources (needed for Gravatar, Cloudflare)

---

## Pre-existing features deployed

These uncommitted changes were compiled and deployed during this session:

- User profiles with custom CSS, bio, headers, accent colors, layouts, embeds
- Blog posts on user profiles
- Status reply threading with collapsible sections
- Notifications system (bell, list, read/unread, dismiss)
- Infinite scroll on timeline with reply grouping
- SSE/EventSource for live reload in development
