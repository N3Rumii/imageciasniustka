# Changelog — szurubooru modifications

> All changes made to the original [rr-/szurubooru](https://github.com/rr-/szurubooru) codebase.

---

## New Features

### 1. Automatic AVIF Conversion (Images)

All uploaded images (PNG, JPEG, BMP, WebP, HEIF) are automatically converted to **lossy AVIF** format. The original file is deleted after conversion to minimize storage.

| File | Change |
|------|--------|
| `server/szurubooru/func/images.py` | Added `to_avif(quality, effort)` method using ffmpeg `libaom-av1` |
| `server/szurubooru/func/posts.py` | Added `_generate_post_avif()`, `finalize_post_avif()`, path/URL helpers |
| `server/config.yaml` | Added `avif:` section (quality, effort) |

**Result:** 41MB PNG → 595KB AVIF (~69x compression). Thumbnails also use AVIF.

### 2. Animated GIF → Animated AVIF

Animated GIFs convert directly to animated AVIF instead of creating separate MP4/WebM alternates.

| File | Change |
|------|--------|
| `server/szurubooru/func/images.py` | Added `to_animated_avif()` for animation support |
| `server/szurubooru/func/posts.py` | `_generate_post_avif()` detects animated GIFs and uses animated encoder |
| `server/config.yaml` | Disabled GIF→MP4/WebM alternates (`convert.gif.to_mp4: false`) |

### 3. Automatic AV1 Video Conversion

All uploaded videos (MP4, MOV, WebM) are automatically converted to **AV1 WebM**. Original deleted after conversion.

| File | Change |
|------|--------|
| `server/szurubooru/func/images.py` | Added `to_av1(quality, effort)` using ffmpeg `libsvtav1` |
| `server/szurubooru/func/posts.py` | Added `_generate_post_av1()`, path/URL helpers, `contentUrl` switches to AV1 |
| `server/config.yaml` | Added `av1:` section (enabled, quality, effort) |

### 4. On-Demand Format Download

Download dropdown on post sidebar lets users download in multiple formats. Conversions happen on-the-fly.

| File | Change |
|------|--------|
| `server/szurubooru/api/post_api.py` | Added `GET /api/post/:id/download?format=png\|jpeg\|mp4\|gif` |
| `client/html/post_readonly_sidebar.tpl` | Added download dropdown (AVIF\|PNG for images, AV1\|MP4 for videos, AVIF\|GIF for animations) |
| `client/js/controls/post_readonly_sidebar_control.js` | Added `_downloadConverted()` handler |

### 5. Private Posts

Posts can be made private (only uploader + whitelisted users can view). Unauthorized users get 403 rejection.

| File | Change |
|------|--------|
| `server/szurubooru/model/post.py` | Added `PostWhitelist` table, `whitelist_users` relationship, `is_private` property |
| `server/szurubooru/func/posts.py` | Added `_can_view_post()`, `update_post_whitelist()`, visibility filter in `get_post_by_id` |
| `server/szurubooru/api/post_api.py` | Added `GET/POST /api/post/:id/whitelist`, `private` + `whitelist` params to create |
| `server/szurubooru/search/configs/post_search_config.py` | Added `_exclude_invisible_posts()` filter |
| `client/html/post_upload.tpl` | Added Private checkbox + whitelist input |
| `client/html/post_readonly_sidebar.tpl` | Shows lock icon + whitelisted users |
| `client/js/views/post_upload_view.js` | Wires private toggle |
| `client/js/controllers/post_upload_controller.js` | Passes private/whitelist data |
| `client/js/models/post.js` | Added `isPrivate`, `whitelist` fields |
| `server/szurubooru/migrations/versions/b1e2f3c4d5e6_*.py` | Migration for `post_whitelist` table |

### 6. Private Galleries

Galleries (pools) can be made private with the same whitelist logic as posts. Private galleries don't affect the visibility of individual posts within them.

| File | Change |
|------|--------|
| `server/szurubooru/model/pool.py` | Added `PoolWhitelist` table, `whitelist_users` relationship, `is_private` property |
| `server/szurubooru/func/pools.py` | Added `update_pool_whitelist()`, serializer fields |
| `server/szurubooru/api/pool_api.py` | Added `private` + `whitelist` params to create |
| `server/szurubooru/search/configs/pool_search_config.py` | Added `_exclude_invisible_pools()` filter |
| `client/html/pool_create.tpl` | Added Private checkbox + whitelist input |
| `client/html/pool_summary.tpl` | Shows lock icon for private galleries |
| `client/js/views/pool_create_view.js` | Wires private toggle |
| `server/szurubooru/migrations/versions/c2d3e4f5a6b7_*.py` | Migration for `pool_whitelist` table |

### 7. Gallery Thumbnail Grid

Gallery summary page now shows a thumbnail grid of contained posts instead of just text.

| File | Change |
|------|--------|
| `client/html/pool_summary.tpl` | Added thumbnail grid section |
| `client/css/pool-view.styl` | Added `.gallery-posts .thumbnail-grid` styles |

### 8. Endless Scroll Image Browser

"Browse" button on post list opens a fullscreen infinite-scroll viewer with lazy loading, keyboard navigation, and autoplay. Supports images and videos.

| File | Change |
|------|--------|
| `client/js/views/post_browser_view.js` | New fullscreen browser with IntersectionObserver, arrow key nav, Space autoplay, skip-videos toggle |
| `client/css/post-browser.styl` | Fullscreen overlay styles |
| `client/html/posts_header.tpl` | Added "Browse" button |
| `client/js/views/posts_header_view.js` | Wired browse event |
| `client/js/controllers/post_list_controller.js` | Added `_evtBrowse()`, fetches all matching posts |

### 9. UI Rename: Pools → Galleries

All user-facing labels changed from "Pool"/"Pools" to "Gallery"/"Galleries". Backend API routes remain unchanged.

| Files | Change |
|-------|--------|
| `client/html/pool*.tpl`, `client/js/controllers/pool*.js`, `client/js/views/pool*.js`, `client/css/pool*.styl` | Renamed labels |
| `client/js/models/top_navigation.js` | Navigation shows "Galleries" |

### 10. Removed "Search on" Links + Simplified TOS

| File | Change |
|------|--------|
| `client/html/post_readonly_sidebar.tpl` | Removed IQDB/Danbooru/Google Images search links |
| `client/html/help_tos.tpl` | Simplified to "no cp or zooporn" |
| `server/config.yaml` | Site renamed to "hosting ciasniutka" |

---

## Removed Features

- **Gallery slideshow** — replaced by the Browse feature
  - Removed: `pool_slideshow_view.js`, `pool_slideshow.tpl`, `pool-slideshow.styl`, slideshow route and tab

---

## Bug Fixes & Compatibility

| Issue | Fix |
|-------|-----|
| **Alpine 3.13→3.19** | Updated server Dockerfile base image + added `--break-system-packages` for pip |
| **SQLAlchemy 2.0** | Fixed `select([...])`→`select(...)` in 6 model files, `sa.events`→`sa.event`, raw SQL→`sa.text()` |
| **Docker buildx** | Removed `--platform=$BUILDPLATFORM` from Dockerfiles (buildx not installed) |
| **Nginx permissions** | Changed nginx user to root, fixed symlink breakage in startup script, increased proxy timeout to 600s |
| **Gallery list empty** | Fixed template variable names broken by rename (`pool`→`gallery`), privilege strings, template references |
| **Gallery tabs broken** | Fixed `gallery-content-holder`→`pool-content-holder` CSS class mismatch, merge variable `targetGalleryId`→`targetPoolId` |
| **AVIF muxer crash** | Changed `to_avif()` to write to temp file instead of stdout (avif muxer requires seekable output) |
| **AV1 encoder** | Switched from `libaom-av1` (broken in Alpine) to `libsvtav1` (SVT-AV1) |
| **AV1 file size** | Tuned CRF mapping for better compression (quality 20 → CRF ~56) |
| **Download endpoint** | Switched from PIL to ffmpeg (PIL AVIF plugin had setter bug) |
| **Search cache** | Fixed anonymous search results being cached and returned for logged-in users |
| **Search config** | Fixed SA 2.0 subquery coercion in post and pool search filters |
| **Metadata update** | Fixed file_size/mime_type not persisting by calling `finalize_post_avif()` after session flush |
| **Content URL** | Only serves AVIF/AV1 if the file actually exists (prevents 404 during background conversion) |

---

## Server Config Additions

```yaml
# config.yaml additions
name: hosting ciasniutka

avif:
    quality: 50
    effort: 4

av1:
    enabled: true
    quality: 20
    effort: 8

privileges:
    'pools:list':   anonymous
    'pools:view':   anonymous

convert:
   gif:
     to_webm: false
     to_mp4: false
```
