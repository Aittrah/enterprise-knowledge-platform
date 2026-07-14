import { FormEvent, useEffect, useRef, useState } from "react";
import { useSearchParams } from "react-router-dom";
import { AgentInfo, api, chatSocket, Citation } from "../lib/api";
import { AnswerText, Seal } from "../components/ui";

interface Message {
  role: "user" | "assistant";
  text: string;
  agentId?: string;
  citations?: Citation[];
  grounded?: boolean;
  streaming?: boolean;
}

export default function Chat() {
  const [params] = useSearchParams();
  const [agents, setAgents] = useState<AgentInfo[]>([]);
  const [agentId, setAgentId] = useState<string>("");
  const [conversationId, setConversationId] = useState<string | null>(
    params.get("c"),
  );
  const [messages, setMessages] = useState<Message[]>([]);
  const [input, setInput] = useState("");
  const [busy, setBusy] = useState(false);
  const socketRef = useRef<WebSocket | null>(null);
  const bottomRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    api.agents().then(setAgents).catch(() => {});
  }, []);

  useEffect(() => {
    const existing = params.get("c");
    if (existing) {
      api
        .history(existing)
        .then((history) =>
          setMessages(
            history.map((m) => ({
              role: m.role as "user" | "assistant",
              text: m.content,
            })),
          ),
        )
        .catch(() => {});
    }
  }, [params]);

  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [messages]);

  function send(event: FormEvent) {
    event.preventDefault();
    const question = input.trim();
    if (!question || busy) return;
    setInput("");
    setBusy(true);
    setMessages((m) => [
      ...m,
      { role: "user", text: question },
      { role: "assistant", text: "", streaming: true },
    ]);

    const socket = chatSocket();
    socketRef.current = socket;
    socket.onopen = () =>
      socket.send(
        JSON.stringify({
          question,
          agent_id: agentId || undefined,
          conversation_id: conversationId || undefined,
        }),
      );
    socket.onmessage = (event) => {
      const message = JSON.parse(event.data);
      setMessages((current) => {
        const next = [...current];
        const last = { ...next[next.length - 1] };
        if (message.type === "start") {
          last.agentId = message.agent_id;
        } else if (message.type === "token") {
          last.text += message.text;
        } else if (message.type === "done") {
          last.streaming = false;
          last.citations = message.citations;
          last.grounded = message.grounded;
          setConversationId(message.conversation_id);
          setBusy(false);
          socket.close();
        } else if (message.type === "error") {
          last.streaming = false;
          last.text = `Something went wrong: ${message.detail}`;
          setBusy(false);
          socket.close();
        }
        next[next.length - 1] = last;
        return next;
      });
    };
    socket.onerror = () => {
      setBusy(false);
      setMessages((current) => {
        const next = [...current];
        const last = next[next.length - 1];
        if (last.streaming) {
          next[next.length - 1] = {
            ...last,
            streaming: false,
            text: "Connection lost — check that the backend is running, then try again.",
          };
        }
        return next;
      });
    };
  }

  const lastCitations =
    [...messages].reverse().find((m) => m.citations?.length)?.citations ?? [];

  return (
    <div className="flex h-screen">
      <div className="flex-1 flex flex-col min-w-0">
        <div className="px-6 py-3 border-b border-edge flex items-center gap-3">
          <label htmlFor="agent" className="text-xs text-ink-muted">
            Agent
          </label>
          <select
            id="agent"
            className="focusable bg-surface-1 border border-edge rounded-lg text-sm px-3 py-1.5"
            value={agentId}
            onChange={(e) => setAgentId(e.target.value)}
          >
            <option value="">Auto-route</option>
            {agents.map((agent) => (
              <option key={agent.id} value={agent.id}>
                {agent.name}
              </option>
            ))}
          </select>
          {conversationId && (
            <span className="font-mono text-[11px] text-ink-muted ml-auto">
              {conversationId}
            </span>
          )}
        </div>

        <div className="flex-1 overflow-y-auto px-6 py-6 space-y-6">
          {messages.length === 0 && (
            <div className="h-full flex items-center justify-center">
              <div className="text-center max-w-md">
                <p className="font-display text-2xl text-ink-muted">
                  Ask your documents anything.
                </p>
                <p className="text-sm text-ink-muted mt-2">
                  Answers stream in with citations you can verify in the
                  provenance panel.
                </p>
              </div>
            </div>
          )}
          {messages.map((message, index) =>
            message.role === "user" ? (
              <div key={index} className="flex justify-end anim-fade-up">
                <div className="bg-verdigris-soft border border-edge rounded-2xl rounded-br-sm px-4 py-3 max-w-[80%] text-[15px]">
                  {message.text}
                </div>
              </div>
            ) : (
              <div key={index} className="max-w-[90%] anim-fade-up">
                <div className="flex items-center gap-2 mb-1.5">
                  <span className="font-mono text-[11px] text-ink-muted uppercase">
                    {message.agentId ?? "agent"}
                  </span>
                  {message.grounded !== undefined && (
                    <Seal grounded={message.grounded} />
                  )}
                </div>
                <div className="card px-4 py-3">
                  {message.text ? (
                    <AnswerText text={message.text} />
                  ) : (
                    <span className="text-ink-muted animate-pulse">thinking…</span>
                  )}
                  {message.streaming && message.text && (
                    <span className="inline-block w-2 h-4 bg-verdigris ml-1 animate-pulse" />
                  )}
                </div>
                {message.role === "assistant" && !message.streaming && message.text && (
                  <button
                    className="focusable text-[11px] text-ink-muted hover:text-ink mt-1.5"
                    onClick={() => navigator.clipboard.writeText(message.text)}
                  >
                    Copy answer
                  </button>
                )}
              </div>
            ),
          )}
          <div ref={bottomRef} />
        </div>

        <form onSubmit={send} className="p-4 border-t border-edge">
          <div className="flex gap-3">
            <input
              className="focusable flex-1 bg-surface-1 border border-edge rounded-xl px-4 py-3 text-sm placeholder:text-ink-muted/60"
              placeholder="Ask about your documents…"
              value={input}
              onChange={(e) => setInput(e.target.value)}
              disabled={busy}
            />
            <button
              className="btn-primary rounded-xl px-5 text-sm disabled:opacity-50"
              disabled={busy || !input.trim()}
            >
              Send
            </button>
          </div>
        </form>
      </div>

      {/* Provenance rail — the signature element (Module 21) */}
      <aside className="w-80 shrink-0 border-l border-edge bg-surface-1 overflow-y-auto hidden xl:block">
        <div className="px-5 py-4 border-b border-edge">
          <h2 className="text-xs uppercase tracking-wider text-ink-muted">Provenance</h2>
        </div>
        {lastCitations.length === 0 ? (
          <p className="text-sm text-ink-muted p-5">
            Sources cited by the latest answer appear here.
          </p>
        ) : (
          <ul className="p-4 space-y-3">
            {lastCitations.map((citation) => (
              <li key={citation.n} className="card p-3.5 border-marginalia/20 anim-fade-up">
                <div className="flex items-center justify-between">
                  <span className="font-mono text-[12px] text-marginalia">
                    [{citation.n}]
                  </span>
                  <span className="font-mono text-[11px] text-verdigris">
                    ◉ {(citation.score * 100).toFixed(0)}%
                  </span>
                </div>
                <div className="text-sm mt-1 break-all">{citation.source}</div>
                {citation.heading_path.length > 0 && (
                  <div className="text-[11px] text-ink-muted mt-1">
                    {citation.heading_path.join(" › ")}
                  </div>
                )}
              </li>
            ))}
          </ul>
        )}
      </aside>
    </div>
  );
}
