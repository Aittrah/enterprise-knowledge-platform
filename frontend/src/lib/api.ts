/** Typed API client. All requests carry the session token. */

import { useSession } from "../stores/session";

export interface User {
  id: number;
  email: string;
  name: string;
  role: string;
}

export interface Citation {
  n: number;
  source: string;
  chunk_id: string;
  heading_path: string[];
  score: number;
  excerpt?: string;
}

export interface ChatResponse {
  conversation_id: string;
  agent_id: string;
  text: string;
  citations: Citation[];
  invalid_citations: number[];
  grounded: boolean;
  retrieval_ms: number;
}

export interface AgentInfo {
  id: string;
  name: string;
  description: string;
}

export interface DocumentInfo {
  filename: string;
  title: string;
  file_type: string;
  size_bytes: number;
  version: number;
  chunks: number;
  entities: number;
  warnings: string[];
  indexed_at: string;
}

export interface AnalyticsSummary {
  documents: number;
  chunks: number;
  conversations: number;
  queries: number;
  prompt_tokens: number;
  completion_tokens: number;
  queries_by_agent: Record<string, number>;
  graph: { entities: number; relations: number };
  embedding_cache: { hits: number; misses: number };
  providers: { embedding: string; llm: string; vector_store: string };
}

export interface GraphViz {
  nodes: { id: string; label: string; type: string; mentions: number; degree: number }[];
  edges: { source: string; target: string; type: string; evidence: string }[];
}

export interface WidgetKey {
  kid: string;
  label: string;
  created_at: string;
  revoked: boolean;
}

export interface WidgetKeyCreated extends WidgetKey {
  token: string;
}

export class ApiError extends Error {
  constructor(
    public status: number,
    detail: string,
  ) {
    super(detail);
  }
}

// When deployed (e.g. frontend on Vercel, backend on a container host), set
// VITE_API_BASE to the backend origin. Empty default = same-origin, which is
// what the local dev proxy and the docker/nginx setup both rely on.
export const API_BASE = (import.meta.env.VITE_API_BASE ?? "").replace(/\/$/, "");

async function request<T>(path: string, options: RequestInit = {}): Promise<T> {
  const token = useSession.getState().token;
  const headers: Record<string, string> = {
    ...(options.headers as Record<string, string>),
  };
  if (token) headers.Authorization = `Bearer ${token}`;
  if (options.body && typeof options.body === "string") {
    headers["Content-Type"] = "application/json";
  }
  const response = await fetch(`${API_BASE}${path}`, { ...options, headers });
  if (response.status === 401 && token) {
    useSession.getState().clear();
  }
  if (!response.ok) {
    let detail = response.statusText;
    try {
      detail = (await response.json()).detail ?? detail;
    } catch {
      /* non-JSON error body */
    }
    throw new ApiError(response.status, String(detail));
  }
  return response.json() as Promise<T>;
}

export const api = {
  register: (email: string, password: string, name: string) =>
    request<{ access_token: string; user: User }>("/api/auth/register", {
      method: "POST",
      body: JSON.stringify({ email, password, name }),
    }),
  login: (email: string, password: string) =>
    request<{ access_token: string; user: User }>("/api/auth/login", {
      method: "POST",
      body: JSON.stringify({ email, password }),
    }),
  me: () => request<User>("/api/auth/me"),
  updateProfile: (body: {
    email?: string;
    name?: string;
    current_password?: string;
    new_password?: string;
  }) =>
    request<User>("/api/auth/me", { method: "PATCH", body: JSON.stringify(body) }),

  agents: () => request<AgentInfo[]>("/api/chat/agents"),
  chat: (question: string, agent_id?: string, conversation_id?: string) =>
    request<ChatResponse>("/api/chat", {
      method: "POST",
      body: JSON.stringify({ question, agent_id, conversation_id }),
    }),
  conversations: () => request<string[]>("/api/chat/conversations"),
  history: (id: string) =>
    request<{ role: string; content: string; created_at: string }[]>(
      `/api/chat/conversations/${id}`,
    ),

  documents: () => request<DocumentInfo[]>("/api/documents"),
  job: (id: string) =>
    request<{ status: string; error?: string }>(`/api/documents/jobs/${id}`),
  upload: (file: File) => {
    const form = new FormData();
    form.append("file", file);
    return request<{ job_id: string; filename: string }>("/api/documents/upload", {
      method: "POST",
      body: form,
    });
  },

  search: (query: string, top_k = 8) =>
    request<{
      hits: { id: string; score: number; text: string; source: string }[];
      strategy: string;
      elapsed_ms: number;
    }>("/api/search", { method: "POST", body: JSON.stringify({ query, top_k }) }),

  graphViz: () => request<GraphViz>("/api/graph/viz"),
  analytics: () => request<AnalyticsSummary>("/api/analytics/summary"),

  widgetKeys: () => request<WidgetKey[]>("/api/widget-keys"),
  createWidgetKey: (label: string) =>
    request<WidgetKeyCreated>("/api/widget-keys", {
      method: "POST",
      body: JSON.stringify({ label }),
    }),
  revokeWidgetKey: (kid: string) =>
    request<void>(`/api/widget-keys/${kid}`, { method: "DELETE" }),
};

export function chatSocket(): WebSocket {
  const token = useSession.getState().token ?? "";
  // Derive the WS origin from API_BASE when the backend is on another host,
  // otherwise fall back to the page origin (dev proxy / nginx).
  const base = API_BASE || location.origin;
  const wsBase = base.replace(/^http/, "ws");
  return new WebSocket(
    `${wsBase}/api/chat/ws?token=${encodeURIComponent(token)}`,
  );
}
