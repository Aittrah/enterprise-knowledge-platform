# Milestone 19 — Frontend

**App:** `frontend/` — Vite + React 18 + TypeScript (strict) + Tailwind v4 + Zustand + Recharts

## Run it

```bash
# terminal 1 — API
cd backend && uvicorn app.api.main:create_app --factory --port 8000
# terminal 2 — web (proxies /api and the websocket to :8000)
cd frontend && npm install && npm run dev
```

`.claude/launch.json` defines both servers (`ekip-api`, `ekip-web`).

## Screens

| Screen | Highlights |
|---|---|
| **Login / Register** | JWT session (Zustand-persisted); first account becomes admin; SSO buttons present, wired at deployment |
| **Dashboard** | serif greeting, stat cards (documents, chunks, queries, tokens), recent conversations, quick actions |
| **AI Chat** | **WebSocket streaming** with typing cursor, agent selector (auto-route or pinned), groundedness **seal** on every answer, citation tags rendered in marginalia amber, copy-answer, and the **Provenance rail** — cited sources with match scores and heading paths |
| **Knowledge Base** | drag-and-drop upload zone → live job status polling → documents table (type, version, chunks, entities, status seal with warnings) |
| **Knowledge Graph** | dependency-free force layout (SVG), nodes colored/sized by type and degree, node search, click-to-focus with dimming, **evidence panel** quoting the sentence behind each relationship |
| **Analytics** | queries-by-agent chart (Recharts), token counters, embedding-cache hit rate, live provider readout; auto-refreshes |
| **Settings** | profile + active providers, with `.env` configuration guidance |

## Verified end-to-end (real browser)

Registered an account → uploaded an HR policy → asked "How many annual leave days do employees get?" → answer streamed over the WebSocket, routed to the **HR agent**, sealed **◉ grounded**, cited `[1]` resolving in the provenance rail → graph page showed Sara Khan / Finance / Bilal Ahmed with evidence sentences → analytics reflected 1 query (hr), 1 document, 7 entities, 9 relations. Zero console errors.

## Scoping notes (deliberate)

- Dark theme only for now; light mode, skeletons-everywhere, and the full component polish are **Module 21** work, gated on design approval of `docs/design/design-system.md`.
- Answer rendering is a minimal safe formatter (bold/code/citations); full markdown + code highlighting arrives with Module 21.
- Bundle is one chunk (~576 kB, mostly Recharts) — code-splitting is a Module 21 task.
