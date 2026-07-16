import { FormEvent, useEffect, useState } from "react";
import { AnalyticsSummary, API_BASE, api, ApiError, WidgetKey } from "../lib/api";
import { PageHeader } from "../components/ui";
import { useSession } from "../stores/session";
import { useUi } from "../stores/ui";

const input =
  "focusable w-full bg-surface-0 border border-edge rounded-lg px-3.5 py-2.5 text-sm placeholder:text-ink-muted/60";

function widgetSnippet(apiBase: string, token: string): string {
  const scriptSrc = `${window.location.origin}/widget/ekip-widget.js`;
  return `<script src="${scriptSrc}"\n  data-api="${apiBase}"\n  data-key="${token}"\n  async></script>`;
}

export default function Settings() {
  const { user, setUser } = useSession();
  const { theme, toggleTheme } = useUi();
  const [summary, setSummary] = useState<AnalyticsSummary | null>(null);

  const [name, setName] = useState(user?.name ?? "");
  const [email, setEmail] = useState(user?.email ?? "");
  const [profileMsg, setProfileMsg] = useState<{ ok: boolean; text: string } | null>(null);

  const [currentPw, setCurrentPw] = useState("");
  const [newPw, setNewPw] = useState("");
  const [pwMsg, setPwMsg] = useState<{ ok: boolean; text: string } | null>(null);

  const [widgetKeys, setWidgetKeys] = useState<WidgetKey[]>([]);
  const [newLabel, setNewLabel] = useState("");
  const [freshSnippet, setFreshSnippet] = useState<string | null>(null);
  const [copied, setCopied] = useState(false);
  const [widgetError, setWidgetError] = useState("");

  const refreshWidgetKeys = () => api.widgetKeys().then(setWidgetKeys).catch(() => {});

  useEffect(() => {
    api.analytics().then(setSummary).catch(() => {});
    refreshWidgetKeys();
  }, []);

  async function saveProfile(e: FormEvent) {
    e.preventDefault();
    setProfileMsg(null);
    try {
      const updated = await api.updateProfile({
        name: name !== user?.name ? name : undefined,
        email: email !== user?.email ? email : undefined,
      });
      setUser(updated);
      setProfileMsg({ ok: true, text: "Profile saved." });
    } catch (err) {
      setProfileMsg({
        ok: false,
        text: err instanceof ApiError ? err.message : "Could not save profile",
      });
    }
  }

  async function changePassword(e: FormEvent) {
    e.preventDefault();
    setPwMsg(null);
    try {
      await api.updateProfile({ current_password: currentPw, new_password: newPw });
      setCurrentPw("");
      setNewPw("");
      setPwMsg({ ok: true, text: "Password changed." });
    } catch (err) {
      setPwMsg({
        ok: false,
        text: err instanceof ApiError ? err.message : "Could not change password",
      });
    }
  }

  async function generateKey() {
    setWidgetError("");
    try {
      const created = await api.createWidgetKey(newLabel.trim() || "Website widget");
      setFreshSnippet(widgetSnippet(API_BASE || window.location.origin, created.token));
      setNewLabel("");
      refreshWidgetKeys();
    } catch (err) {
      setWidgetError(err instanceof ApiError ? err.message : "Could not create a widget key");
    }
  }

  async function revokeKey(kid: string) {
    try {
      await api.revokeWidgetKey(kid);
      refreshWidgetKeys();
    } catch {
      /* the list refresh below will still reflect the true server state */
    }
  }

  return (
    <div className="pb-10">
      <PageHeader title="Settings" sub="Profile, appearance and platform configuration." />
      <div className="px-8 grid lg:grid-cols-2 gap-4 max-w-4xl stagger">
        <section className="card p-5">
          <h2 className="text-sm text-ink-muted uppercase tracking-wider mb-4">Profile</h2>
          <form onSubmit={saveProfile} className="space-y-3">
            <label className="block text-[11px] text-ink-muted uppercase">
              Name
              <input className={`${input} mt-1`} value={name} onChange={(e) => setName(e.target.value)} />
            </label>
            <label className="block text-[11px] text-ink-muted uppercase">
              Email
              <input
                className={`${input} mt-1`}
                type="email"
                value={email}
                onChange={(e) => setEmail(e.target.value)}
              />
            </label>
            {profileMsg && (
              <p className={`text-sm anim-fade-up ${profileMsg.ok ? "text-verdigris" : "text-signal"}`}>
                {profileMsg.text}
              </p>
            )}
            <button className="btn-primary px-4 py-2 text-sm" disabled={!name || !email}>
              Save changes
            </button>
          </form>
        </section>

        <section className="card p-5">
          <h2 className="text-sm text-ink-muted uppercase tracking-wider mb-4">Password</h2>
          <form onSubmit={changePassword} className="space-y-3">
            <label className="block text-[11px] text-ink-muted uppercase">
              Current password
              <input
                className={`${input} mt-1`}
                type="password"
                value={currentPw}
                onChange={(e) => setCurrentPw(e.target.value)}
                autoComplete="current-password"
              />
            </label>
            <label className="block text-[11px] text-ink-muted uppercase">
              New password (min 8 characters)
              <input
                className={`${input} mt-1`}
                type="password"
                value={newPw}
                minLength={8}
                onChange={(e) => setNewPw(e.target.value)}
                autoComplete="new-password"
              />
            </label>
            {pwMsg && (
              <p className={`text-sm anim-fade-up ${pwMsg.ok ? "text-verdigris" : "text-signal"}`}>
                {pwMsg.text}
              </p>
            )}
            <button className="btn-primary px-4 py-2 text-sm" disabled={!currentPw || newPw.length < 8}>
              Change password
            </button>
          </form>
        </section>

        <section className="card p-5">
          <h2 className="text-sm text-ink-muted uppercase tracking-wider mb-4">Appearance</h2>
          <div className="flex items-center justify-between">
            <div className="text-sm">
              Theme
              <div className="text-[12px] text-ink-muted">Light by default; dark for late nights.</div>
            </div>
            <button
              className="focusable border border-edge rounded-lg px-4 py-2 text-sm hover:bg-hover transition-colors"
              onClick={toggleTheme}
            >
              {theme === "light" ? "◑ Switch to dark" : "◐ Switch to light"}
            </button>
          </div>
        </section>

        <section className="card p-5">
          <h2 className="text-sm text-ink-muted uppercase tracking-wider mb-4">Active providers</h2>
          {summary ? (
            <dl className="space-y-3 text-sm">
              <div>
                <dt className="text-[11px] text-ink-muted uppercase">LLM</dt>
                <dd className="mt-0.5 font-mono text-[13px]">{summary.providers.llm}</dd>
              </div>
              <div>
                <dt className="text-[11px] text-ink-muted uppercase">Embedding model</dt>
                <dd className="mt-0.5 font-mono text-[13px]">{summary.providers.embedding}</dd>
              </div>
              <div>
                <dt className="text-[11px] text-ink-muted uppercase">Vector store</dt>
                <dd className="mt-0.5 font-mono text-[13px]">{summary.providers.vector_store}</dd>
              </div>
            </dl>
          ) : (
            <div className="space-y-2">
              <div className="shimmer h-4 w-40 rounded" />
              <div className="shimmer h-4 w-32 rounded" />
            </div>
          )}
          <p className="text-[12px] text-ink-muted mt-5 pt-4 border-t border-edge leading-relaxed">
            Providers are configured in the backend <span className="font-mono">.env</span> — set{" "}
            <span className="font-mono">OPENAI_API_KEY</span> for synthesized answers.
          </p>
        </section>

        <section className="card p-5 lg:col-span-2">
          <h2 className="text-sm text-ink-muted uppercase tracking-wider mb-1">Embed widget</h2>
          <p className="text-[12px] text-ink-muted mb-4">
            Add this platform's chat to any website — no login required for visitors. Each
            key only opens the chat widget; it can never reach your documents or admin
            settings even if someone reads it out of your page's HTML.
          </p>

          <div className="flex gap-2 mb-4">
            <input
              className={input}
              placeholder="Label (e.g. Marketing site)"
              value={newLabel}
              onChange={(e) => setNewLabel(e.target.value)}
              maxLength={80}
            />
            <button className="btn-primary px-4 py-2 text-sm whitespace-nowrap" onClick={generateKey}>
              Generate key
            </button>
          </div>
          {widgetError && <p className="text-signal text-sm mb-3">{widgetError}</p>}

          {freshSnippet && (
            <div className="anim-fade-up mb-5">
              <div className="flex items-center justify-between mb-1.5">
                <p className="text-[12px] text-ink-muted">
                  Paste this into your site's HTML — shown only once, so save it now:
                </p>
                <button
                  className="focusable text-[11px] text-ink underline underline-offset-4"
                  onClick={() => {
                    navigator.clipboard.writeText(freshSnippet);
                    setCopied(true);
                    setTimeout(() => setCopied(false), 1500);
                  }}
                >
                  {copied ? "Copied!" : "Copy"}
                </button>
              </div>
              <pre className="bg-surface-0 border border-edge rounded-lg p-3 text-[11.5px] font-mono overflow-x-auto whitespace-pre-wrap break-all">
                {freshSnippet}
              </pre>
            </div>
          )}

          {widgetKeys.length > 0 && (
            <div className="border-t border-edge pt-4">
              <table className="w-full text-sm">
                <thead>
                  <tr className="text-left text-[11px] uppercase tracking-wider text-ink-muted">
                    <th className="pb-2">Label</th>
                    <th className="pb-2">Created</th>
                    <th className="pb-2">Status</th>
                    <th className="pb-2" />
                  </tr>
                </thead>
                <tbody>
                  {widgetKeys.map((key) => (
                    <tr key={key.kid} className="border-t border-edge">
                      <td className="py-2">{key.label}</td>
                      <td className="py-2 font-mono text-[11px] text-ink-muted">
                        {new Date(key.created_at).toLocaleDateString()}
                      </td>
                      <td className="py-2">
                        {key.revoked ? (
                          <span className="text-signal font-mono text-[11px]">revoked</span>
                        ) : (
                          <span className="text-verdigris font-mono text-[11px]">◉ active</span>
                        )}
                      </td>
                      <td className="py-2 text-right">
                        {!key.revoked && (
                          <button
                            className="focusable text-[11px] text-ink-muted hover:text-signal"
                            onClick={() => revokeKey(key.kid)}
                          >
                            Revoke
                          </button>
                        )}
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          )}
        </section>
      </div>
    </div>
  );
}
