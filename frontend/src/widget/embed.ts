/**
 * EKIP embeddable chat widget.
 *
 * Framework-free by design: this file has zero imports, so the built
 * bundle is a single small IIFE any site can load with one <script> tag.
 * It renders into a Shadow DOM root so the host page's CSS can never leak
 * in (or the widget's CSS leak out) — safe to drop onto any website.
 *
 * Usage:
 *   <script src="https://your-ekip-host/widget/ekip-widget.js"
 *           data-api="https://your-ekip-host"
 *           data-key="<widget key from Settings -> Embed Widget>"
 *           async></script>
 *
 * Optional attributes: data-agent, data-title, data-position (bottom-right
 * default | bottom-left), data-theme (dark default | light).
 */

interface WidgetConfig {
  api: string;
  key: string;
  agent?: string;
  title: string;
  position: "bottom-right" | "bottom-left";
  theme: "dark" | "light";
}

interface StreamMessage {
  type: "start" | "token" | "done" | "error";
  text?: string;
  agent_id?: string;
  conversation_id?: string;
  citations?: { n: number; source: string }[];
  grounded?: boolean;
  detail?: string;
}

const DARK = {
  bg: "#0a0a0a",
  panel: "#121212",
  edge: "#262626",
  ink: "#f4f4f4",
  inkMuted: "#979490",
  accent: "#ffffff",
  accentContrast: "#0a0a0a",
  bubble: "#1f1f1f",
  grounded: "#35c29a",
  unverified: "#d9a45b",
};
const LIGHT = {
  bg: "#ffffff",
  panel: "#ffffff",
  edge: "#e6e3de",
  ink: "#201f1e",
  inkMuted: "#6b6862",
  accent: "#171717",
  accentContrast: "#ffffff",
  bubble: "#eceae7",
  grounded: "#0e7a63",
  unverified: "#9a6a00",
};

function readConfig(script: HTMLScriptElement): WidgetConfig {
  const d = script.dataset;
  if (!d.api || !d.key) {
    throw new Error("EKIP widget: data-api and data-key are required");
  }
  return {
    api: d.api.replace(/\/$/, ""),
    key: d.key,
    agent: d.agent,
    title: d.title ?? "Ask this site",
    position: d.position === "bottom-left" ? "bottom-left" : "bottom-right",
    theme: d.theme === "light" ? "light" : "dark",
  };
}

function wsUrl(api: string, key: string): string {
  return `${api.replace(/^http/, "ws")}/api/widget/chat/ws?key=${encodeURIComponent(key)}`;
}

function escapeHtml(text: string): string {
  const div = document.createElement("div");
  div.textContent = text;
  return div.innerHTML;
}

/** Bold/citation-tag rendering only — deliberately minimal to keep the
 * bundle tiny; full markdown lives in the dashboard app. */
function renderAnswer(text: string): string {
  return escapeHtml(text)
    .replace(/\[(\d+)\]/g, '<span class="cite">[$1]</span>')
    .replace(/\*\*([^*]+)\*\*/g, "<strong>$1</strong>");
}

function init(script: HTMLScriptElement): void {
  const config = readConfig(script);
  const palette = config.theme === "light" ? LIGHT : DARK;
  const storageKey = `ekip_widget_convo_${config.key.slice(-12)}`;

  const host = document.createElement("div");
  host.style.all = "initial";
  document.body.appendChild(host);
  const root = host.attachShadow({ mode: "open" });

  const side = config.position === "bottom-left" ? "left" : "right";
  root.innerHTML = `
    <style>
      :host, * { box-sizing: border-box; font-family: -apple-system, "Segoe UI", system-ui, sans-serif; }
      .wrap { position: fixed; bottom: 20px; ${side}: 20px; z-index: 2147483000; }
      .launcher {
        width: 56px; height: 56px; border-radius: 50%; border: none; cursor: pointer;
        background: ${palette.accent}; color: ${palette.accentContrast};
        box-shadow: 0 8px 24px rgba(0,0,0,0.35);
        display: flex; align-items: center; justify-content: center;
        transition: transform 200ms cubic-bezier(.34,1.56,.64,1);
      }
      .launcher:hover { transform: scale(1.06); }
      .launcher svg { width: 26px; height: 26px; }
      .panel {
        position: absolute; bottom: 72px; ${side}: 0;
        width: 360px; max-width: calc(100vw - 40px); height: 520px; max-height: 70vh;
        background: ${palette.panel}; border: 1px solid ${palette.edge}; border-radius: 16px;
        display: none; flex-direction: column; overflow: hidden;
        box-shadow: 0 20px 60px rgba(0,0,0,0.45);
        animation: rise 220ms cubic-bezier(.2,.8,.2,1);
      }
      .panel.open { display: flex; }
      @keyframes rise { from { opacity: 0; transform: translateY(12px); } to { opacity: 1; transform: translateY(0); } }
      .head { padding: 14px 16px; border-bottom: 1px solid ${palette.edge}; display: flex; align-items: center; justify-content: space-between; }
      .head h1 { font-size: 14px; font-weight: 600; color: ${palette.ink}; margin: 0; }
      .head button { background: none; border: none; color: ${palette.inkMuted}; cursor: pointer; font-size: 18px; line-height: 1; padding: 4px; }
      .msgs { flex: 1; overflow-y: auto; padding: 14px 16px; display: flex; flex-direction: column; gap: 12px; }
      .msg { font-size: 13.5px; line-height: 1.5; color: ${palette.ink}; }
      .msg.user { align-self: flex-end; background: ${palette.bubble}; padding: 8px 12px; border-radius: 14px 14px 4px 14px; max-width: 85%; }
      .msg.bot { max-width: 100%; }
      .meta { display: flex; align-items: center; gap: 6px; font-size: 10.5px; color: ${palette.inkMuted}; margin-top: 6px; }
      .dot { width: 6px; height: 6px; border-radius: 50%; }
      .cite { color: ${palette.unverified}; font-family: ui-monospace, monospace; font-size: 11px; }
      .empty { color: ${palette.inkMuted}; font-size: 13px; text-align: center; margin: auto; padding: 0 20px; }
      .row { padding: 12px; border-top: 1px solid ${palette.edge}; display: flex; gap: 8px; }
      .row input {
        flex: 1; background: transparent; border: 1px solid ${palette.edge}; border-radius: 10px;
        padding: 9px 12px; font-size: 13px; color: ${palette.ink}; outline: none;
      }
      .row input::placeholder { color: ${palette.inkMuted}; }
      .row button {
        background: ${palette.accent}; color: ${palette.accentContrast}; border: none; border-radius: 10px;
        padding: 0 16px; font-size: 13px; font-weight: 500; cursor: pointer;
      }
      .row button:disabled { opacity: 0.5; cursor: default; }
      .footer { text-align: center; padding: 6px 0 10px; font-size: 10px; color: ${palette.inkMuted}; }
      .footer a { color: inherit; }
      @media (max-width: 480px) {
        .panel { position: fixed; inset: 0; bottom: 0; width: 100%; height: 100%; max-height: 100%; border-radius: 0; }
        .wrap { ${side}: 16px; bottom: 16px; }
      }
    </style>
    <div class="wrap">
      <div class="panel" role="dialog" aria-label="${escapeHtml(config.title)}">
        <div class="head">
          <h1>${escapeHtml(config.title)}</h1>
          <button class="close" aria-label="Close chat">&times;</button>
        </div>
        <div class="msgs"><div class="empty">Ask a question about this site's documents.</div></div>
        <div class="row">
          <input type="text" placeholder="Type your question…" aria-label="Message" />
          <button class="send">Send</button>
        </div>
        <div class="footer">Powered by <a href="https://github.com/Aittrah/enterprise-knowledge-platform" target="_blank" rel="noopener">EKIP</a></div>
      </div>
      <button class="launcher" aria-label="Open chat">
        <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
          <path d="M21 11.5a8.38 8.38 0 0 1-.9 3.8 8.5 8.5 0 0 1-7.6 4.7 8.38 8.38 0 0 1-3.8-.9L3 21l1.9-5.7a8.38 8.38 0 0 1-.9-3.8 8.5 8.5 0 0 1 4.7-7.6 8.38 8.38 0 0 1 3.8-.9h.5a8.48 8.48 0 0 1 8 8v.5z"/>
        </svg>
      </button>
    </div>
  `;

  const panel = root.querySelector<HTMLDivElement>(".panel")!;
  const launcher = root.querySelector<HTMLButtonElement>(".launcher")!;
  const closeBtn = root.querySelector<HTMLButtonElement>(".close")!;
  const msgs = root.querySelector<HTMLDivElement>(".msgs")!;
  const input = root.querySelector<HTMLInputElement>(".row input")!;
  const sendBtn = root.querySelector<HTMLButtonElement>(".row button")!;

  let conversationId: string | null = null;
  try {
    conversationId = localStorage.getItem(storageKey);
  } catch {
    /* storage may be unavailable (privacy mode) — fine, just don't persist */
  }
  let socket: WebSocket | null = null;
  let busy = false;

  function toggle(open: boolean): void {
    panel.classList.toggle("open", open);
    if (open) input.focus();
  }
  launcher.addEventListener("click", () => toggle(!panel.classList.contains("open")));
  closeBtn.addEventListener("click", () => toggle(false));

  function clearEmptyState(): void {
    const empty = msgs.querySelector(".empty");
    if (empty) empty.remove();
  }

  function addUserMessage(text: string): void {
    clearEmptyState();
    const el = document.createElement("div");
    el.className = "msg user";
    el.textContent = text;
    msgs.appendChild(el);
    msgs.scrollTop = msgs.scrollHeight;
  }

  function addBotMessage(): HTMLDivElement {
    const el = document.createElement("div");
    el.className = "msg bot";
    el.innerHTML = '<span class="body">…</span>';
    msgs.appendChild(el);
    msgs.scrollTop = msgs.scrollHeight;
    return el;
  }

  function send(): void {
    const question = input.value.trim();
    if (!question || busy) return;
    input.value = "";
    busy = true;
    sendBtn.disabled = true;
    addUserMessage(question);
    const botEl = addBotMessage();
    const body = botEl.querySelector<HTMLSpanElement>(".body")!;
    let text = "";

    socket = new WebSocket(wsUrl(config.api, config.key));
    socket.onopen = () =>
      socket!.send(
        JSON.stringify({
          question,
          agent_id: config.agent,
          conversation_id: conversationId,
        }),
      );
    socket.onmessage = (event) => {
      const message: StreamMessage = JSON.parse(event.data);
      if (message.type === "token") {
        text += message.text ?? "";
        body.innerHTML = renderAnswer(text);
      } else if (message.type === "done") {
        conversationId = message.conversation_id ?? conversationId;
        if (conversationId) {
          try {
            localStorage.setItem(storageKey, conversationId);
          } catch {
            /* ignore */
          }
        }
        const grounded = !!message.grounded;
        const meta = document.createElement("div");
        meta.className = "meta";
        const sources = message.citations?.length
          ? `${message.citations.length} source${message.citations.length > 1 ? "s" : ""}`
          : "no sources";
        meta.innerHTML = `<span class="dot" style="background:${grounded ? palette.grounded : palette.unverified}"></span>${grounded ? "Grounded" : "Unverified"} · ${sources}`;
        botEl.appendChild(meta);
        busy = false;
        sendBtn.disabled = false;
        socket?.close();
      } else if (message.type === "error") {
        body.textContent = `Something went wrong: ${message.detail}`;
        busy = false;
        sendBtn.disabled = false;
      }
      msgs.scrollTop = msgs.scrollHeight;
    };
    socket.onerror = () => {
      body.textContent = "Connection lost. Please try again.";
      busy = false;
      sendBtn.disabled = false;
    };
  }

  sendBtn.addEventListener("click", send);
  input.addEventListener("keydown", (event) => {
    if (event.key === "Enter") send();
  });
}

(function bootstrap() {
  const current = document.currentScript as HTMLScriptElement | null;
  try {
    init(
      current ??
        (document.querySelector("script[data-api][data-key]") as HTMLScriptElement),
    );
  } catch (error) {
    console.error(error);
  }
})();
