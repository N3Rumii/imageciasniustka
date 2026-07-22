# REASONIX.md — szurubooru (hosting ciasniutka)

## Stack
- **Backend:** Python 3 — custom WSGI REST framework (no Flask/Django)
- **Frontend:** Vanilla JS SPA, built with Browserify + Babel + Stylus
- **Database:** PostgreSQL via SQLAlchemy ORM (<1.4) + Alembic migrations
- **Image processing:** Pillow (avif plugin), pyheif, numpy
- **Video:** yt-dlp for URL retrieval

## Layout
- `server/szurubooru/api/` — REST endpoint handlers
- `server/szurubooru/func/` — business logic (posts, tags, users, auth, files…)
- `server/szurubooru/model/` — SQLAlchemy ORM models
- `server/szurubooru/rest/` — custom WSGI framework (app, routing, middleware)
- `server/szurubooru/search/` — query parser and search executor
- `server/szurubooru/migrations/` — Alembic schema migrations
- `server/szurubooru/tests/` — pytest suite (mirrors source structure)
- `client/js/` — JS frontend: controllers, models, views, controls
- `client/css/` — Stylus stylesheets
- `client/html/` — HTML templates (index.htm is entry point)
- `doc/` — API docs, install guide, example env
- `scripts/` — run-server-tests.sh
- `tools/` — img_viewer.py dev utility

## Commands
- **Build (client):** `npm run build`  (runs `node build.js` — Browserify + Babel + minify)
- **Watch (client):** `npm run watch`  (rebuilds on file change)
- **Test (server):** `scripts/run-server-tests.sh`  (builds Docker image, runs pytest -n auto)
- **Lint/Format:** `pre-commit run --all-files`  (black + isort + flake8 for Python; prettier + eslint for JS)

## Conventions
- **Python:** black (line-length 79), isort (szurubooru = first-party), flake8 (ignores F401, W503, W504, E203, E231)
- **JavaScript:** prettier (printWidth 79, tabWidth 4), eslint with prettier config; ES6 + Browserify
- **pre-commit enforced:** trailing whitespace, EOF newline, no tabs, YAML lint; `fail_fast: true`

## Watch out for
- Server reads config from `config.yaml` — copy `server/config.yaml.dist` to start
- Tests run **inside Docker** (pytest-xdist); the runner script builds the image first
- `server/szurubooru/migrations/` is Alembic-managed — don't edit migration scripts manually
- `.pre-commit-config.yaml` uses `fail_fast: true` — first hook failure aborts the run
