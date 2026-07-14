import { FormEvent, useEffect, useState } from "react";
import { AnalyticsSummary, api, ApiError } from "../lib/api";
import { PageHeader } from "../components/ui";
import { useSession } from "../stores/session";
import { useUi } from "../stores/ui";

const input =
  "focusable w-full bg-surface-0 border border-edge rounded-lg px-3.5 py-2.5 text-sm placeholder:text-ink-muted/60";

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

  useEffect(() => {
    api.analytics().then(setSummary).catch(() => {});
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
      </div>
    </div>
  );
}
