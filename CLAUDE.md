# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Start here

Read `MEMORY.md` and `AGENT.md` before doing anything else. `AGENT.md` contains the full set of
product decisions, behavioral rules, and hard stops for this repo (originally written for Codex,
but they apply to any agent working here — Claude included). `MEMORY.md` is a running decision log;
append to it after any significant decision about direction, format, content, approach, or
strategy, using the format defined at the top of `AGENT.md`. Never contradict a logged decision
without flagging it first.

Key things from `AGENT.md` worth internalizing up front:
- This is a **two-branch** (Ashesi University, Abelemkpe — always spelled `Abelemkpe`) WhatsApp-first
  restaurant ordering platform. Customers order in the web app; WhatsApp is the receipt/notification/
  support/tracking-return channel, not the ordering channel itself.
- The database is the order source of truth. Never build notification or tracking logic that runs
  on independent timers instead of recorded order state.
- Backend-calculated pricing is authoritative — never trust totals submitted by the browser.
- Deploys, migrations against real databases, and any message/API call to real recipients require
  explicit in-session confirmation — no exceptions, and "you mentioned this earlier" doesn't count.
- Stay surgical: touch only what the current task requires, don't refactor adjacent code, don't
  reorganize files that aren't part of the task.

## Commands

### Frontend (`frontend/`, Next.js 14 + TypeScript + Tailwind)
```bash
cd frontend
npm install
npm run dev      # dev server
npm run build    # production build — part of the standard verification baseline
npm run lint     # next lint
```

### Backend (`backend/`, FastAPI + Python)
```bash
cd backend
python -m venv venv && source venv/bin/activate
uv pip install -r requirements.txt   # or: pip install -r requirements.txt
uvicorn app.main:app --reload
```

Run tests from the repo root (conftest.py stubs required env vars — no real `.env` needed for tests):
```bash
PYTHONPATH=backend python3 -m pytest backend/tests
```
Single file / single test:
```bash
PYTHONPATH=backend python3 -m pytest backend/tests/test_order_api.py
PYTHONPATH=backend python3 -m pytest backend/tests/test_order_api.py::test_name -v
```

### Standard verification baseline
Run both before considering a change done:
```bash
cd frontend && npm run build
PYTHONPATH=backend python3 -m pytest backend/tests
```
For order, payment, branch, tracking, or WhatsApp changes, also walk the end-to-end checklist in
`AGENT.md` under "Verification Expectations" — build/tests alone don't verify Supabase migrations,
Meta webhook configuration, or deployed runtime behavior.

## Architecture

```
Customer → Next.js web app (frontend/) → FastAPI backend (backend/) → Supabase (Postgres)
                                                    ↓
                                     Meta WhatsApp Cloud API (receipts, tracking links, status notifications)
```

**Backend** (`backend/app/`): FastAPI app assembled in `main.py`, which mounts routers from
`app/routers/`:
- `public.py` — unauthenticated endpoints (menu browsing, order tracking by token)
- `orders.py` — order placement and status transitions
- `menu.py` — menu/branch/availability data
- `auth.py` / `admin.py` — staff auth and admin/dashboard endpoints
- `webhook.py` — Meta WhatsApp webhook (inbound messages, delivery/read receipts)

Business logic lives in `app/services/`, not in routers — e.g. `order_service.py` (order lifecycle
and `order_events` audit trail), `branch_service.py`, `menu_service.py`, `notification_service.py`
and `whatsapp.py` (outbound WhatsApp sends), `order_parser.py` + `ai_service.py`/`groq_service.py`
(AI-assisted order parsing, Groq primary → OpenAI → Gemini fallback chain), `auth_service.py`,
`customer_service.py`, `session_store.py`, `rate_limit.py`. Request/response shapes are in
`app/schemas/`. `app/config.py` defines all env-driven settings (`Settings`, loaded via
`get_settings()`); `app/database.py` exposes a cached Supabase client via `get_supabase()`.

Order state is tracked via an append-only `order_events` audit trail (see
`backend/migrations/0004_order_operations.sql`) — status transitions must go through the service
layer so they stay validated and audited; don't write ad-hoc status updates.

**Database**: `backend/migrations/*.sql` are additive, numbered, and must be run in order in the
Supabase SQL editor (see `backend/migrations/README.md`). The app still writes to the legacy
`orders.items` JSON column alongside newer normalized tables — both are currently live. Tenant/
branch config: tenant slug `default-tenant`, branch codes `ASHESI` and `ABELEMKPE`. Public tracking
tokens expire after 90 days by default.

**Frontend** (`frontend/src/`): Next.js Pages Router. `pages/index.tsx` is the ordering flow
(branch → menu → cart → checkout), `pages/track/[token].tsx` is the public order-tracking page,
`pages/admin/*` and `pages/dashboard.tsx` are staff-facing. Shared UI in `src/components/`
(`BranchPicker`, `CartDrawer`/`CartSidebar`, `FoodCard`, `ProductSheet`, etc.), API/data helpers in
`src/lib/`, and a service worker (`public/sw.js`) + manifest for installable/PWA behavior.

**Docs worth checking before larger changes**: `docs/PRODUCTION_ARCHITECTURE_PLAN.md` (architecture
decisions — keep in sync when architecture changes), `docs/TWO_BRANCH_ORDERING_CHECKLIST.md`
(update as launch work completes), `docs/OPERATIONS_RUNBOOK.md`, `docs/PROVISIONAL_LAUNCH_DATA.md`.
