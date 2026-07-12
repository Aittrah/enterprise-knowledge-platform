# Module 21 — UI/UX Design Direction & Design System

**Status: awaiting approval** — per the Module 21 workflow, no frontend code is written until this direction is approved (feedback, screenshots, and inspiration images welcome).

---

## 1. Design thesis

EKIP's product promise is **provenance**: every answer can prove where it came from. The interface should feel like *a reading room wired into a control room* — the calm, archival trust of a research library combined with the operational precision of tools like Linear and the Vercel dashboard.

What this is **not**: a generic chatbot skin, a cream-and-terracotta landing page, or a black dashboard with one neon accent. Every aesthetic choice below traces back to the provenance thesis.

## 2. Signature element — the Provenance Rail

The one thing users will remember. In AI Chat, a persistent right-hand rail holds the cited passages. Each citation in the answer is a small monospaced tag — `[1]`, `[2]` — underlined in *marginalia amber*; hovering it draws a hairline thread from the tag to its source card in the rail, and the card lifts. Each source card shows document title, page/section, a two-line excerpt, and a **groundedness stamp** (a small circular meter, like an archivist's seal). Low-confidence answers get an amber "unverified" seal instead of green — trust is displayed, never implied.

The same seal + mono-tag language reappears across the app (document cards show embedding status as a seal; analytics show hallucination rate with the same meter), so the signature is a system, not a one-off decoration.

## 3. Color tokens

Dark mode is the primary theme (enterprise AI tooling context); light mode is first-class, not an inversion afterthought.

| Token | Dark | Light | Role |
|---|---|---|---|
| `--surface-0` | `#0C1220` deep archive blue-slate | `#F7F8F7` cool paper | App background — *never pure black/white* |
| `--surface-1` | `#131B2C` | `#FFFFFF` | Cards, panels |
| `--ink` | `#E8EBEA` | `#1A2230` | Primary text |
| `--ink-muted` | `#8A93A6` | `#5A6474` | Secondary text, labels |
| `--verdigris` | `#2E9E83` | `#177B63` | Primary accent — actions, active nav, focus. The patina of old brass in libraries: trustworthy, aged, alive |
| `--marginalia` | `#E0A458` | `#B97F2E` | Citations, annotations, "needs review" states — the highlighter/pencil color of a careful reader |
| `--signal-red` | `#E5484D` | `#CE2C31` | Errors, hallucination flags only |

Rule: verdigris = *the system acting*, marginalia = *the system citing or asking for human judgment*, red = *the system failing*. Color is semantics, not decoration.

## 4. Typography

| Role | Face | Usage |
|---|---|---|
| Display | **Source Serif 4** (600) | Page titles, empty-state headlines, onboarding — the archival voice. Used sparingly: one serif moment per screen |
| UI / Body | **Instrument Sans** | Everything interactive: nav, buttons, forms, paragraphs |
| Data / Meta | **IBM Plex Mono** | Citation tags, token counts, costs, timestamps, IDs, statuses — anything a machine measured |

Scale (8-pt aligned): 12 / 13 / 14 (base) / 16 / 20 / 28 / 36. Weights: 400/500 for UI, 600 for display. Mono always one step smaller than surrounding body.

The mix is the identity: *serif says "knowledge", sans says "product", mono says "evidence".*

## 5. Layout system

- 8-pt spacing grid; card radius 10 px; hairline borders (`1px`, 8 % ink) instead of drop shadows in dark mode
- Persistent left sidebar (72 px collapsed / 248 px expanded) + slim top bar with global ⌘K command palette
- Content max-width 1440 px; data screens use full width, reading screens (chat) cap at comfortable measure
- Motion: 150–200 ms ease-out on hover/focus; one orchestrated moment per screen (e.g., provenance thread draw ~250 ms). `prefers-reduced-motion` respected globally

## 6. Screen wireframes

### AI Chat (the flagship)
```
┌──────┬──────────────────────────────────────┬────────────────────┐
│ nav  │ HR Agent ▾   ●grounded 92%           │ PROVENANCE         │
│      │ ────────────────────────────────     │ ┌───────────────┐  │
│ hist │  You: annual leave policy?           │ │[1] Leave.pdf  │  │
│ ory  │                                      │ │ p.4 §2 ◉ 96%  │  │
│ list │  ⬡ Answer streams here with          │ │ "Employees    │  │
│      │  inline citation tags [1] [2]        │ │  accrue 22…"  │  │
│      │  connected by threads → rail         │ ├───────────────┤  │
│      │                                      │ │[2] HB-2024    │  │
│      │ ┌──────────────────────────────┐     │ │ p.11 ◉ 88%    │  │
│      │ │ Ask about your documents… 🎤 📎│     │ └───────────────┘  │
│      │ └──────────────────────────────┘     │ suggested questions│
└──────┴──────────────────────────────────────┴────────────────────┘
```
Streaming markdown + code highlighting, copy/export per message, agent selector with the six domain agents, voice input, file drop anywhere onto the thread.

### Dashboard
```
┌──────┬─────────────────────────────────────────────────────────┐
│ nav  │ Serif greeting: "Good morning, Aittrah"    [⌘K search]  │
│      │ ┌────────┐┌────────┐┌────────┐┌────────┐                │
│      │ │Tokens  ││API cost││Docs    ││Storage │  ← mono figures│
│      │ └────────┘└────────┘└────────┘└────────┘                │
│      │ ┌───────────────────────┐ ┌─────────────────────┐       │
│      │ │ AI usage (area chart) │ │ Active agents (6)   │       │
│      │ └───────────────────────┘ └─────────────────────┘       │
│      │ ┌───────────────────────┐ ┌─────────────────────┐       │
│      │ │ Recent conversations  │ │ KB stats + quick    │       │
│      │ │                       │ │ actions (upload…)   │       │
│      │ └───────────────────────┘ └─────────────────────┘       │
└──────┴─────────────────────────────────────────────────────────┘
```

### Auth (Login / Register / Forgot / SSO)
Split screen: left = form on `surface-0` (email/password, Google + Microsoft SSO buttons, sentence-case microcopy); right = a quiet animated rendition of the provenance thread motif over the serif product statement. No stock illustration.

### Knowledge Base
Toolbar (search, filters: type/category/tag/status) → switchable table/card grid of documents. Each card: file-type glyph, title, metadata in mono, version chip, OCR + embedding **seals**. Row click opens preview drawer with version history timeline.

### Knowledge Graph
Full-bleed canvas (force layout), typed nodes (People / Departments / Documents) in the token palette, expand/collapse on click, node search top-left, detail side panel with connected entities. Legend uses the same seals.

### Analytics
KPI row (query volume, avg latency, hallucination rate ◉, cost) + charts grid (Recharts): query trends, retrieval accuracy, token consumption by agent, feedback trends. Hallucination + accuracy reuse the groundedness meter language.

### Admin
Tabbed: Users & Roles (data table, role chips) · Documents · Providers & Models (adapter cards with health dots) · API Keys (mono, masked) · Monitoring · Feedback.

### Settings
Two-column: nav list (Profile, LLM Provider, Embedding Model, Theme, Language, Notifications, Security, API Keys) → form panels, React Hook Form + zod validation, instant theme preview.

## 7. Component library (shadcn/ui base + custom)

Sidebar · TopNav · ChatWindow · MessageBubble · CitationTag + ProvenanceRail · GroundednessSeal · DocumentCard · SearchBar/CommandPalette · StatCard · DataTable · Modal · Toast · ProgressSeal · Timeline · GraphViewer · ChartKit · FileUploadZone · Breadcrumbs · EmptyState · Skeleton set

## 8. Quality floor (every screen)

8-pt spacing · loading skeletons · designed empty states (serif headline + one clear action) · error states that say what happened and how to fix it · success toasts · full keyboard navigation + visible focus rings (verdigris) · WCAG 2.1 AA contrast (all token pairs checked) · responsive to 360 px · dark/light parity.

## 9. Self-critique (pre-approval)

- *Risk taken:* serif display + mono evidence in an enterprise SaaS — justified because "knowledge" is the product; kept safe by restricting serif to one moment per screen.
- *Rejected defaults:* cream/terracotta editorial look; black + acid green; hairline broadsheet grid — none serve provenance.
- *Watch item:* the provenance thread animation must degrade to a simple highlight under `prefers-reduced-motion` and on mobile (rail becomes a bottom sheet).

**Next step per Module 21 workflow:** review this direction → approve or give feedback (screenshots/inspiration welcome) → then per-screen wireframe review before React implementation at Milestone 19.
