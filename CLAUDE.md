# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Commands

**Backend tests** — there is no local virtualenv; tests run in the image:

```bash
docker compose build backend
docker run --rm --entrypoint pytest ai-lead-automation-backend          # all tests
docker run --rm --entrypoint pytest ai-lead-automation-backend tests/test_slack.py::test_with_query_param_on_url_with_existing_query
```

`backend/tests/conftest.py` sets `APP_ENCRYPTION_KEY` / `SETUP_TOKEN` /
`DATABASE_URL` before app import, since `Settings` has no defaults for the
first two. The current tests exercise pure functions only — no DB or network.

**Full stack**:

```bash
cp .env.example .env && ./scripts/gen-secrets.sh >> .env   # first time only
docker compose up -d --build
docker compose logs -f backend n8n
```

Frontend: `http://localhost:3000` (form), `/setup` (wizard). n8n editor:
`http://localhost:5678`. Backend is not published to the host — reach it with
`docker compose exec backend curl localhost:8000/...`.

**Frontend build/lint** (from `frontend/`, pnpm): `pnpm build`, `pnpm lint`,
`pnpm dev`. `next build` statically analyzes routes that read env vars, so a
bare `pnpm build` fails without `BACKEND_URL`, `SETUP_TOKEN`, and
`N8N_WEBHOOK_URL` set — see the placeholder `ENV` lines in `frontend/Dockerfile`.

**Migrations**: applied automatically by `backend/entrypoint.sh`
(`alembic upgrade head`) on every container start. To author one:
`docker compose exec backend alembic revision --autogenerate -m "..."`.

## Architecture

Four services in `docker-compose.yml`. The division of labor: **n8n
orchestrates, FastAPI holds all business logic, Next.js is the only human
surface, Postgres stores both lead state and encrypted credentials.**

### Orchestration lives in JSON, not code

`n8n/workflows/lead-pipeline.json` (workflow id `leadpipeline0001`) is the
pipeline's control flow. `n8n/entrypoint.sh` imports and publishes it before
`n8n start` — the CLI writes directly to the DB, so this must happen while n8n
is stopped. On restart the import is skipped if the workflow already exists
(preserving UI edits) unless `N8N_FORCE_REIMPORT=true`.

**Consequence: the workflow JSON hardcodes `http://backend:8000/leads/...`
URLs and reads specific response fields.** Renaming a `/leads` route, changing
a request body, or renaming a response key (`lead_id`, `is_duplicate`,
`website_url`) requires editing the node's `parameters` in the JSON too, then
redeploying with `N8N_FORCE_REIMPORT=true`. Nodes chain by name via
`$('Normalize Lead').item.json.lead_id`, so renaming a node breaks downstream
expressions.

### Request path for one lead

```
LeadForm → POST /api/lead (Next.js proxy, honeypot check)
         → n8n Webhook "lead-intake"
         → POST /leads/normalize          → is_duplicate? stop : continue
         → (n8n GET's website_url, neverError, 10s timeout)
         → POST /leads/{id}/enrich        (LLM, or {"available": false})
         → POST /leads/{id}/draft         (LLM structured content → rendered subject/body)
         → POST /leads/{id}/request-approval  (Slack post, passes $execution.resumeUrl)
         → n8n Wait node (webhook resume, 7-day limit)
         → POST /leads/{id}/send  |  PATCH /leads/{id}/status
```

The Wait node's resume webhook is called by `/approval` (Next.js, server-side),
not clicked directly — see "Slack approval is URL buttons" below.

Scraping happens in **n8n**, not the backend — the backend receives raw HTML in
`scraped_html` and only parses/summarizes it (`app/services/enrich.py`).

### Emails are auto-translated and branded, not model-generated HTML

`app/services/draft.py` never returns markup. The LLM returns structured
content (`language`, `greeting`, `paragraphs`, `cta_label`, `signoff`), with
the language auto-detected from the lead's submitted message (falling back to
the website enrichment language, then to `business.default_language`).
`app/services/email_render.py` is the **only** module that knows HTML — it
renders that structured content into a table-based, inline-CSS email using
the `branding` config, plus a matching plain-text version. `lead.draft_body`
(plain text) is what's stored for backwards compatibility and posted to
Slack for approval; `lead.draft_body_html` is the new multipart alternative
sent via `mailer.send_outreach_email(..., html_body=...)`. Never let the LLM
emit raw HTML into `paragraphs` — `email_render` escapes everything it
interpolates and validates URLs are http(s), which only holds if content stays
data, not markup.

### Slack approval is URL buttons, not interactive actions

`app/services/slack.py` posts buttons whose `url` is our own `/approval` page
(`{PUBLIC_APP_URL}/approval?resume=...&lead=...`), built by
`build_approval_link()`. This deliberately avoids requiring Slack
Interactivity (a public Request URL) during setup — a plain `url` button is
enough. The embedded `resume` param is n8n's per-execution resume URL with
`?decision=approve|reject` already merged in via `_with_query_param()`
(regression-tested in `tests/test_slack.py`); naive appending breaks n8n's
`?signature=...` check.

`/approval` (`frontend/app/approval/page.tsx` + `frontend/lib/approval.ts`)
resumes that n8n webhook **server-side** and renders a branded confirmation —
the approver's browser never sees n8n's raw JSON response, and never needs
network access to n8n at all. `resumeApproval()` allowlists the resume URL's
origin/path against `N8N_BASE_URL` before fetching it, since the URL arrives
as untrusted query-string input; skipping that check would make the page an
SSRF pivot into the Docker network. The buttons are only clickable from
wherever `PUBLIC_APP_URL` points, so remote approvers need a real reachable
URL there — n8n itself no longer needs to be publicly reachable.

### Credentials: encrypted in Postgres, not env vars

Only `OPENAI_MODEL` and secrets-for-secrets live in `.env`. The OpenAI key,
SMTP login, Slack token, business info, and (optional) branding are entered
through `/setup`, **live-tested against the real service** (branding has no
external service to test, so it's just saved), then Fernet-encrypted into the
`app_config` table (`app/crypto.py`, keyed by `APP_ENCRYPTION_KEY`). Unlike
the other config keys, `branding` has a `GET /config/branding` route too — it
holds no secrets, and the wizard needs to read it back to pre-fill the step
without wiping fields on the next save (`save_config` is a full replace, not a
merge).

- Read them with `get_config(db, key)` — returns `None` unless `is_verified`.
- Consumers raise `HTTPException(409, "... not configured yet")` on `None`;
  follow that pattern for any new credential-dependent route.
- Rotating `APP_ENCRYPTION_KEY` orphans existing rows (`DecryptionError`) —
  the wizard must be re-run.
- Config test failures surface the provider's own error text as
  `HTTPException(400, ...)` so `/setup` can show it verbatim. Preserve that.

### Auth model: one shared secret, three hops

There are no user accounts. `SETUP_TOKEN` from `.env` is held by both the
backend and the Next.js server:

1. Browser posts the token to `/api/setup/authorize`; `lib/auth.ts` compares it
   and sets the `la_setup_session` **httpOnly** cookie.
2. `app/api/config/[...path]/route.ts` checks that cookie, then attaches the
   real `X-Setup-Token` header server-side.
3. Backend `require_setup_token` (`app/routers/config.py`) validates the header.

The token never reaches client-side JS, and `BACKEND_URL` / `N8N_BASE_URL`
stay server-only (`import "server-only"`). Keep new config endpoints behind
this same proxy rather than calling the backend from the browser.

### Backend layout conventions

`app/routers/` = HTTP shape and lead-status transitions only; `app/services/`
= the actual work (`normalize`, `enrich`, `draft`, `mailer`, `slack`). Nothing
outside `app/llm.py` imports `openai` — it exposes an `LLMProvider` Protocol
(`complete_json` / `complete_text`) so a second provider is one class plus a
branch in `get_provider()`.

Lead status advances `new → normalized → enriched → draft_ready →
approved|rejected → sent|failed`; it's a Postgres enum (`lead_status`), so
adding a value needs a migration. The router that performs a step also sets the
status.
