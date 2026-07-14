import { FormEvent, useState } from "react";
import { api, ApiError } from "../lib/api";
import { useSession } from "../stores/session";

export default function Login() {
  const signIn = useSession((s) => s.signIn);
  const [mode, setMode] = useState<"login" | "register">("login");
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [name, setName] = useState("");
  const [error, setError] = useState("");
  const [busy, setBusy] = useState(false);

  async function submit(event: FormEvent) {
    event.preventDefault();
    setError("");
    setBusy(true);
    try {
      const result =
        mode === "login"
          ? await api.login(email, password)
          : await api.register(email, password, name);
      signIn(result.access_token, result.user);
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "Cannot reach the API — is the backend running?");
    } finally {
      setBusy(false);
    }
  }

  const input =
    "focusable w-full bg-surface-0 border border-white/10 rounded-lg px-3.5 py-2.5 text-sm placeholder:text-ink-muted/60";

  return (
    <div className="min-h-screen grid lg:grid-cols-2">
      <div className="flex items-center justify-center p-8">
        <form onSubmit={submit} className="w-full max-w-sm space-y-4">
          <div className="mb-8">
            <div className="font-display text-3xl">EKIP</div>
            <p className="text-ink-muted text-sm mt-2">
              {mode === "login"
                ? "Sign in to your knowledge base."
                : "Create your account. The first account becomes the admin."}
            </p>
          </div>
          {mode === "register" && (
            <input
              className={input}
              placeholder="Full name"
              value={name}
              onChange={(e) => setName(e.target.value)}
              required
            />
          )}
          <input
            className={input}
            type="email"
            placeholder="Work email"
            value={email}
            onChange={(e) => setEmail(e.target.value)}
            required
          />
          <input
            className={input}
            type="password"
            placeholder={mode === "register" ? "Password (min 8 characters)" : "Password"}
            value={password}
            onChange={(e) => setPassword(e.target.value)}
            minLength={mode === "register" ? 8 : undefined}
            required
          />
          {error && <p className="text-signal text-sm">{error}</p>}
          <button
            className="focusable w-full bg-verdigris hover:bg-verdigris-bright text-surface-0 font-medium rounded-lg py-2.5 text-sm transition-colors disabled:opacity-60"
            disabled={busy}
          >
            {busy ? "Working…" : mode === "login" ? "Sign in" : "Create account"}
          </button>
          <div className="pt-2 space-y-2">
            <button
              type="button"
              className="focusable w-full border border-white/10 rounded-lg py-2.5 text-sm text-ink-muted"
              title="SSO is configured at deployment (Module 21)"
              disabled
            >
              Continue with Google — available after SSO setup
            </button>
            <button
              type="button"
              className="focusable w-full border border-white/10 rounded-lg py-2.5 text-sm text-ink-muted"
              title="SSO is configured at deployment (Module 21)"
              disabled
            >
              Continue with Microsoft — available after SSO setup
            </button>
          </div>
          <p className="text-sm text-ink-muted text-center pt-2">
            {mode === "login" ? "No account yet?" : "Already registered?"}{" "}
            <button
              type="button"
              className="focusable text-verdigris-bright"
              onClick={() => setMode(mode === "login" ? "register" : "login")}
            >
              {mode === "login" ? "Create one" : "Sign in"}
            </button>
          </p>
        </form>
      </div>
      <div className="hidden lg:flex items-center justify-center bg-surface-1 border-l border-white/8 p-12">
        <div className="max-w-md">
          <p className="font-display text-2xl leading-snug">
            Every answer traces back to its source.
          </p>
          <p className="text-ink-muted mt-4 text-sm leading-relaxed">
            Hybrid retrieval, knowledge graphs, and six domain agents over your
            documents — with citations verified on every response.
          </p>
          <div className="mt-8 font-mono text-[12px] text-ink-muted space-y-1.5">
            <div>◉ 96% <span className="text-marginalia">[1]</span> leave-policy.pdf · p.4</div>
            <div>◉ 88% <span className="text-marginalia">[2]</span> handbook-2026.docx · §2.1</div>
          </div>
        </div>
      </div>
    </div>
  );
}
