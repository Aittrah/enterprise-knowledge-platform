# Milestone 26 — Embeddable Chat Widget

**Backend:** `backend/app/api/widget_keys.py`, `backend/app/api/routers/widget.py` · **Frontend:** `frontend/src/widget/embed.ts` · **Tests:** `backend/tests/test_widget.py` (12; suite 285)

## What it does

Any EKIP account can generate a key that lets a completely separate website embed EKIP's chat — with **no visitor login** — with one line of HTML:

```html
<script src="https://your-ekip-host/widget/ekip-widget.js"
        data-api="https://your-ekip-host"
        data-key="<key from Settings → Embed widget>"
        async></script>
```

That single script renders a floating chat bubble, opens a streaming chat panel on click, and answers from the account's own knowledge base — fully themed, grounded, and cited, on a page that shares none of EKIP's CSS or JavaScript.

## The security boundary (this is the part that matters)

A widget key lives in **public HTML source** on someone else's site — anyone can view-source it. That makes it fundamentally different from a dashboard session token, so it is deliberately the *least* powerful credential in the system:

- It is a JWT with `scope: "widget"` and a `kid` — nothing else (no email, no role).
- **`get_current_user` explicitly rejects any token with `scope == "widget"`** (`app/api/deps.py`) — so a widget key extracted from a page's HTML can never call `/api/documents`, `/api/auth/users`, or any other dashboard route. Verified by `test_widget_token_cannot_access_dashboard_endpoints`.
- The reverse is also enforced: `/api/widget/chat/ws` rejects ordinary dashboard tokens (`test_widget_websocket_rejects_dashboard_token`) — the two credential types don't cross.
- Keys are **revocable**. `WidgetKeyStore` persists only `(kid, label, revoked)` in SQLite — never the signed token itself (standard "shown once" API-key UX) — and every widget socket connection checks `is_active(kid)` before accepting.

## Why WebSocket-only, no REST fallback

A WebSocket handshake isn't subject to the browser's CORS/Fetch algorithm, so `/api/widget/chat/ws` embeds on **any origin with zero CORS configuration** — one less thing to misconfigure on a public-facing endpoint. Skipping a REST fallback was a deliberate scope decision, not an oversight; it's the one thing to add if a future host environment blocks outbound WebSockets.

## The bundle itself

`embed.ts` has **zero imports** — no React, no shared app code — so it builds to a ~7.7 KB (3 KB gzipped) IIFE via a dedicated Vite config (`vite.widget.config.ts`). It renders into a **Shadow DOM** root, so the host page's CSS can never bleed into the widget and the widget's CSS can never leak onto the host page. Configuration is read from the script tag's `data-*` attributes (`data-agent`, `data-title`, `data-position`, `data-theme`); the conversation id persists in the visitor's `localStorage` so a page reload continues the same thread.

`frontend/public/widget-demo.html` proves the claim concretely: a plain, deliberately unrelated-looking HTML page with the widget embedded and working end-to-end.

## Generating a key

**Settings → Embed widget** in the dashboard: label it, click *Generate key*, copy the one-time snippet. The list below shows every key's status and a *Revoke* action — revoking takes effect on the next connection attempt, no restart required.

**Local development note:** the generated snippet's `data-api` defaults to `window.location.origin`, which is correct for the production docker/nginx setup where the frontend and API share one origin. When running the frontend (`:5173`) and API (`:8000`) separately in dev, set `VITE_API_BASE=http://localhost:8000` so the generated snippet points at the right place — `widget-demo.html` shows the explicit override.
