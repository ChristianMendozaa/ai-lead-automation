"use client";

import { FormEvent, useState } from "react";
import type { ConfigStatus } from "@/lib/config";

type StepKey = "openai" | "smtp" | "slack";
const STEPS: { key: StepKey; title: string }[] = [
  { key: "openai", title: "OpenAI" },
  { key: "smtp", title: "SMTP" },
  { key: "slack", title: "Slack" },
];

async function saveConfig(key: StepKey, payload: Record<string, unknown>) {
  const res = await fetch(`/api/config/${key}`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(payload),
  });
  const data = await res.json().catch(() => ({}));
  if (!res.ok) {
    throw new Error(data.detail ?? `Request failed (${res.status})`);
  }
}

export default function SetupWizard({ initialStatus }: { initialStatus: ConfigStatus }) {
  const [saved, setSaved] = useState({
    openai: initialStatus.openai,
    smtp: initialStatus.smtp,
    slack: initialStatus.slack,
  });
  const firstUnfinished = STEPS.findIndex((s) => !saved[s.key]);
  const [activeIndex, setActiveIndex] = useState(
    firstUnfinished === -1 ? STEPS.length - 1 : firstUnfinished
  );

  const allDone = saved.openai && saved.smtp && saved.slack;
  const active = STEPS[activeIndex];

  function markSaved(key: StepKey) {
    setSaved((prev) => ({ ...prev, [key]: true }));
  }

  return (
    <main className="mx-auto min-h-screen max-w-lg px-4 py-12">
      <h1 className="mb-1 text-2xl font-semibold">Setup</h1>
      <p className="mb-6 text-sm text-slate-600 dark:text-slate-400">
        Connect the three services the lead pipeline needs. Each step must
        pass a real test before you can move on.
      </p>

      <ol className="mb-8 flex gap-2">
        {STEPS.map((step, i) => (
          <li key={step.key} className="flex-1">
            <button
              type="button"
              onClick={() => setActiveIndex(i)}
              className={`w-full rounded-md border px-3 py-2 text-left text-sm transition ${
                i === activeIndex
                  ? "border-slate-900 bg-slate-900 text-white dark:border-slate-100 dark:bg-slate-100 dark:text-slate-900"
                  : "border-slate-300 dark:border-slate-700"
              }`}
            >
              {saved[step.key] ? "✓ " : `${i + 1}. `}
              {step.title}
            </button>
          </li>
        ))}
      </ol>

      {active.key === "openai" && (
        <OpenAIStep saved={saved.openai} onSaved={() => markSaved("openai")} />
      )}
      {active.key === "smtp" && (
        <SmtpStep saved={saved.smtp} onSaved={() => markSaved("smtp")} />
      )}
      {active.key === "slack" && (
        <SlackStep saved={saved.slack} onSaved={() => markSaved("slack")} />
      )}

      <div className="mt-6 flex justify-between">
        <button
          type="button"
          onClick={() => setActiveIndex((i) => Math.max(0, i - 1))}
          disabled={activeIndex === 0}
          className="rounded-md border border-slate-300 px-4 py-2 text-sm disabled:opacity-40 dark:border-slate-700"
        >
          Back
        </button>
        <button
          type="button"
          onClick={() => setActiveIndex((i) => Math.min(STEPS.length - 1, i + 1))}
          disabled={!saved[active.key] || activeIndex === STEPS.length - 1}
          className="rounded-md bg-slate-900 px-4 py-2 text-sm font-medium text-white disabled:opacity-40 dark:bg-slate-100 dark:text-slate-900"
        >
          Next
        </button>
      </div>

      {allDone && (
        <div className="mt-8 rounded-lg border border-emerald-300 bg-emerald-50 p-4 text-sm text-emerald-900 dark:border-emerald-700 dark:bg-emerald-950 dark:text-emerald-200">
          All set! Refresh <a href="/" className="underline">the lead form</a>{" "}
          to start capturing leads.
        </div>
      )}
    </main>
  );
}

function StepShell({
  saved,
  children,
  onSubmit,
  submitting,
  error,
}: {
  saved: boolean;
  children: React.ReactNode;
  onSubmit: (e: FormEvent<HTMLFormElement>) => void;
  submitting: boolean;
  error: string | null;
}) {
  return (
    <form onSubmit={onSubmit} className="space-y-3 rounded-lg border border-slate-200 p-4 dark:border-slate-800">
      {children}
      {error && <p className="text-sm text-red-600 dark:text-red-400">{error}</p>}
      {saved && !error && (
        <p className="text-sm text-emerald-600 dark:text-emerald-400">Verified and saved.</p>
      )}
      <button
        type="submit"
        disabled={submitting}
        className="rounded-md bg-slate-900 px-4 py-2 text-sm font-medium text-white disabled:opacity-60 dark:bg-slate-100 dark:text-slate-900"
      >
        {submitting ? "Testing..." : "Test & Save"}
      </button>
    </form>
  );
}

function Input({
  label,
  ...props
}: React.InputHTMLAttributes<HTMLInputElement> & { label: string }) {
  return (
    <div>
      <label className="mb-1 block text-sm font-medium">{label}</label>
      <input
        {...props}
        className="w-full rounded-md border border-slate-300 bg-white px-3 py-2 text-sm outline-none focus:border-slate-500 dark:border-slate-700 dark:bg-slate-900"
      />
    </div>
  );
}

function OpenAIStep({ saved, onSaved }: { saved: boolean; onSaved: () => void }) {
  const [submitting, setSubmitting] = useState(false);
  const [error, setError] = useState<string | null>(null);

  async function handleSubmit(e: FormEvent<HTMLFormElement>) {
    e.preventDefault();
    setSubmitting(true);
    setError(null);
    const data = Object.fromEntries(new FormData(e.currentTarget).entries());
    try {
      await saveConfig("openai", { api_key: data.api_key });
      onSaved();
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to verify OpenAI key.");
    } finally {
      setSubmitting(false);
    }
  }

  return (
    <StepShell saved={saved} onSubmit={handleSubmit} submitting={submitting} error={error}>
      <p className="text-sm text-slate-600 dark:text-slate-400">
        Used to draft outreach emails and summarize scraped company pages.
        Get a key from{" "}
        <a
          href="https://platform.openai.com/api-keys"
          target="_blank"
          rel="noreferrer"
          className="underline"
        >
          platform.openai.com/api-keys
        </a>
        .
      </p>
      <Input label="OpenAI API key" name="api_key" type="password" required placeholder="sk-..." />
    </StepShell>
  );
}

function SmtpStep({ saved, onSaved }: { saved: boolean; onSaved: () => void }) {
  const [submitting, setSubmitting] = useState(false);
  const [error, setError] = useState<string | null>(null);

  async function handleSubmit(e: FormEvent<HTMLFormElement>) {
    e.preventDefault();
    setSubmitting(true);
    setError(null);
    const data = Object.fromEntries(new FormData(e.currentTarget).entries());
    try {
      await saveConfig("smtp", {
        host: data.host,
        port: Number(data.port),
        username: data.username,
        password: data.password,
        from_address: data.from_address,
        test_recipient: data.test_recipient,
      });
      onSaved();
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to send a test email.");
    } finally {
      setSubmitting(false);
    }
  }

  return (
    <StepShell saved={saved} onSubmit={handleSubmit} submitting={submitting} error={error}>
      <p className="text-sm text-slate-600 dark:text-slate-400">
        Used to send the approved outreach email. For Gmail, use an{" "}
        <a
          href="https://myaccount.google.com/apppasswords"
          target="_blank"
          rel="noreferrer"
          className="underline"
        >
          app password
        </a>
        , not your regular password.
      </p>
      <Input label="SMTP host" name="host" required placeholder="smtp.gmail.com" />
      <Input label="Port" name="port" type="number" required defaultValue={587} />
      <Input label="Username" name="username" required />
      <Input label="Password" name="password" type="password" required />
      <Input label="From address" name="from_address" type="email" required />
      <Input
        label="Send a test email to"
        name="test_recipient"
        type="email"
        required
        placeholder="you@example.com"
      />
    </StepShell>
  );
}

function SlackStep({ saved, onSaved }: { saved: boolean; onSaved: () => void }) {
  const [submitting, setSubmitting] = useState(false);
  const [error, setError] = useState<string | null>(null);

  async function handleSubmit(e: FormEvent<HTMLFormElement>) {
    e.preventDefault();
    setSubmitting(true);
    setError(null);
    const data = Object.fromEntries(new FormData(e.currentTarget).entries());
    try {
      await saveConfig("slack", { bot_token: data.bot_token, channel: data.channel });
      onSaved();
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to post a test Slack message.");
    } finally {
      setSubmitting(false);
    }
  }

  return (
    <StepShell saved={saved} onSubmit={handleSubmit} submitting={submitting} error={error}>
      <div className="text-sm text-slate-600 dark:text-slate-400">
        <p className="mb-1">Drafts are posted here for approval before sending. Quick setup:</p>
        <ol className="ml-4 list-decimal space-y-0.5">
          <li>
            Create an app at{" "}
            <a
              href="https://api.slack.com/apps"
              target="_blank"
              rel="noreferrer"
              className="underline"
            >
              api.slack.com/apps
            </a>
          </li>
          <li>Under &quot;OAuth &amp; Permissions&quot;, add the <code>chat:write</code> scope</li>
          <li>Install the app to your workspace</li>
          <li>Copy the &quot;Bot User OAuth Token&quot; (starts with <code>xoxb-</code>)</li>
          <li>Invite the bot to your target channel: <code>/invite @your-app</code></li>
        </ol>
      </div>
      <Input label="Bot User OAuth token" name="bot_token" type="password" required placeholder="xoxb-..." />
      <Input label="Channel" name="channel" required placeholder="#new-leads" />
    </StepShell>
  );
}
