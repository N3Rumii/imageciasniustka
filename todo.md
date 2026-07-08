# 🔐 Security Audit & Remediation Plan — ciasniutka.pl

> **Date:** 2026-07-07 | **Overall score:** 3.9/10 🟠 Weak

---

## Executive Summary

Full penetration test of the Szurubooru instance hosted at `ciasniutka.pl`. Three critical escalation paths found, all stemming from configuration and deployment issues rather than application code bugs. The Szurubooru codebase itself is well-written — the problems are operational.

**The single worst finding:** PostgreSQL uses `trust` authentication for all local connections. Any process on the device can read/write the entire database without a password.

---

## Scoreboard

| # | Category | Score | Grade |
|---|----------|:-----:|-------|
| 1 | Auth & Password Security | 2/10 | 🔴 Critical |
| 2 | Authorization & Privileges | 6/10 | 🟡 Fair |
| 3 | Database Security | 1/10 | 🔴 Critical |
| 4 | Network & Infrastructure | 5/10 | 🟡 Fair |
| 5 | Input Validation & Injection | 7/10 | 🟢 Good |
| 6 | Session Management & Tokens | 4/10 | 🟠 Weak |
| 7 | Data Protection & Privacy | 5/10 | 🟡 Fair |
| 8 | API Security | 6/10 | 🟢 Good |
| 9 | Security Headers & Browser | 2/10 | 🔴 Critical |
| 10 | Logging, Monitoring & Errors | 3/10 | 🟠 Weak |
| 11 | Configuration & Secrets | 1/10 | 🔴 Critical |
| 12 | Dependencies & Supply Chain | 5/10 | 🟡 Fair |
| **—** | **OVERALL** | **3.9/10** | 🟠 **Weak** |

---

## Critical Findings (C1–C3)

### C1 — PostgreSQL `trust` authentication
**File:** `pgdata/pg_hba.conf` | **Severity:** 🔴 Critical

All local TCP connections (127.0.0.1) and Unix sockets use `trust` method — no password required for ANY PostgreSQL user. Confirmed by dumping all user rows including password hashes and salts via psycopg2 without credentials.

### C2 — Hardcoded secrets in config.yaml
**File:** `server/config.yaml` | **Severity:** 🔴 Critical

- `secret: 0b3c5efc3ac5aa9dc3155910a320125bca2a4131459d9a6428c16a7a111e75fa`
- `database: postgresql://szuru:szuru_password@localhost:5432/szuru`

Two full backups exist with identical secrets: `hosting_cias_backup/` and `hosting_cias_backup_20260707_0029/`.

### C3 — User token exposure via API
**File:** `server/szurubooru/api/user_token_api.py` | **Severity:** 🔴 Critical

Full UUID tokens visible in API responses. Admin can list all tokens (87 total, 42 for admin user `Reny`, most without expiration). Token hijacking trivial with admin access.

---

## High Findings (H1–H5)

### H1 — Open registration with no email verification
`users:create:self: anonymous` in config.yaml. SMTP not configured.

### H2 — Weak password policy
`password_regex: '^.{5,}$'` — only requires 5 characters, no complexity.

### H3 — Debug mode in production
`debug: 1` in config.yaml (appears twice). May leak stack traces.

### H4 — No rate limiting on authentication
No `X-RateLimit-*` headers. Brute-force attacks unthrottled.

### H5 — Secret key used as pepper
Secret concatenated with salt+password before hashing. With secret in config.yaml (C2) and salts in DB (C1), password cracking reduces to single-factor.

---

## Medium Findings (M1–M5)

### M1 — Missing security headers
No CSP, X-Frame-Options, HSTS, X-Content-Type-Options, Referrer-Policy.

### M2 — No CORS configuration
API responses contain no `Access-Control-Allow-Origin` headers.

### M3 — Profile CSS injection (limited)
CSS sanitizer is case-sensitive — `Url(`, `URL(`, `url (` bypass the filter. HTML breakout blocked by `textContent` on client. Data exfiltration via CSS attribute selectors possible.

### M4 — Data directory publicly served
`/data/` served via nginx with 1h public cache. No access control on file serving.

### M5 — CSS sanitizer bypasses
Server-side filter: `url(`, `@import`, `behavior:`, `expression(`, `javascript:` are blocked but only lowercase. Case variants (`Url(`, `URL(`) and whitespace variants (`url (`) pass through. Client-side `textContent` prevents JS execution but CSS data exfiltration remains possible.

---

## Cloudflare WAF Bypass Results

| Attack Vector | Result |
|---------------|--------|
| SQL injection in query string | BLOCKED (HTTP 000) |
| URL-encoded SQL injection | PASSES (HTTP 200) |
| XSS `<script>` in query | BLOCKED (HTTP 406) |
| Path traversal `../` | PASSES (HTTP 200, nginx collapses) |
| `.git/config` access | PASSES (HTTP 200, SPA index returned) |
| Open registration | PASSES (HTTP 200) |
| File upload with auth | PASSES (HTTP 200) |

---

## Remediation Plan

### Phase 1 — Stop the Bleeding (Today)

- [ ] **1.1** Replace PostgreSQL `trust` auth with `scram-sha-256` → `pgdata/pg_hba.conf`
  - Set strong password: `ALTER ROLE szuru WITH PASSWORD '<new-password>';`
  - Update `pg_hba.conf` — only allow `scram-sha-256` for `szuru` database
  - Reload: `pg_ctl reload -D pgdata/`
- [ ] **1.2** Rotate secrets → `server/config.yaml`
  - Generate new 64-char hex secret: `python3 -c "import secrets; print(secrets.token_hex(32))"`
  - Update: `secret: <new-secret>`, `database: postgresql://szuru:<new-pass>@...`
  - Set `debug: 0` (remove duplicate line)
- [ ] **1.3** Restart services in order
  - Reload PostgreSQL, then restart the Python waitress server
  - ⚠️ Rotating secret invalidates all user passwords — users will need password resets

### Phase 2 — Lock Down the App (This Week)

- [ ] **2.1** Strengthen password policy → `server/config.yaml`
  - Change to: `password_regex: '^(?=.*[a-z])(?=.*[A-Z])(?=.*\d).{8,}$'`
  - Update registration form instructions in client HTML
- [ ] **2.2** Restrict registration → `server/config.yaml`
  - Change: `'users:create:self': administrator` (was `anonymous`)
- [ ] **2.3** Add security headers → `nginx.conf`
  - `X-Frame-Options: SAMEORIGIN`
  - `X-Content-Type-Options: nosniff`
  - `Strict-Transport-Security: max-age=31536000; includeSubDomains`
  - `Content-Security-Policy` (baseline, tighten over time)
  - `Referrer-Policy: strict-origin-when-cross-origin`
- [ ] **2.4** Add rate limiting → `nginx.conf`
  - API zone: 10 req/s burst 20
  - Login zone: 5 req/min burst 3
- [ ] **2.5** Fix CSS sanitizer → `server/szurubooru/func/users.py`
  - Replace case-sensitive blacklist with case-insensitive regex:
    ```python
    css = re.sub(r'(?i)url\s*\(', '/* blocked */', css)
    css = re.sub(r'(?i)@\s*import', '/* blocked */', css)
    css = re.sub(r'(?i)expression\s*\(', '/* blocked */', css)
    css = re.sub(r'(?i)behavior\s*:', '/* blocked */', css)
    css = re.sub(r'(?i)javascript\s*:', '/* blocked */', css)
    css = css.replace('<', '').replace('>', '')
    ```
- [ ] **2.6** Restrict nginx data exposure → `nginx.conf`
  - Add: `location /data/temporary-uploads/ { deny all; }`
  - Add: `location /data/posts/ { deny all; }`

### Phase 3 — Defense in Depth (This Month)

- [ ] **3.1** Restrict file permissions
  - `chmod 600 server/config.yaml`
  - `chmod 600 server/config.yaml.dist`
  - Delete or move backup directories (`hosting_cias_backup/`, `hosting_cias_backup_20260707_0029/`)
- [ ] **3.2** Configure Cloudflare WAF rules
  - Rate limit `/api/` endpoints (60 req/min)
  - Block path traversal patterns
  - Enable Bot Fight Mode
- [ ] **3.3** Consider Unix socket for PostgreSQL instead of TCP
- [ ] **3.4** Set up basic log monitoring (cron job scanning for 401/403 spikes)

### Phase 4 — Cleanup

- [ ] **4.1** Delete test accounts: `pentest_attacker`, `cftest_user`, `css_test_user`
- [ ] **4.2** Expire all existing user tokens: `UPDATE user_token SET enabled = false;`
- [ ] **4.3** Remove `.git` directory from production or restrict access

---

## Attack Chains Discovered

### Chain A — Anonymous → Admin (via local DB)
```
Register account → Read config.yaml secrets → Connect PostgreSQL (trust auth)
→ UPDATE user SET rank='administrator' → Full server control
```

### Chain B — Anonymous → Session Hijack (via credential cracking)
```
Register → Brute-force weak passwords → OR dump hashes via C1+C2
→ Crack with known pepper → Login as admin → Steal tokens (C3)
```

### Chain C — Remote → Data Theft (Cloudflare-bypassed)
```
Remote → ciasniutka.pl → Register account (H1) → Enumerate users (API)
→ Brute-force passwords (H2, H4) → Access all posts/comments/data
```

---

## Test Artifacts Created During Audit

| Account | Purpose | Status |
|---------|---------|--------|
| `pentest_attacker` | General API testing, briefly elevated to admin then reverted | ⬜ Needs deletion |
| `cftest_user` | Cloudflare registration bypass test | ⬜ Needs deletion |
| `css_test_user` | CSS sanitizer bypass testing (CSS cleared) | ⬜ Needs deletion |

No data was deleted, corrupted, or exfiltrated. All DB modifications were reverted.
