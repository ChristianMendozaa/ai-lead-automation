"use client";

import { FormEvent, useState } from "react";
import type { ConfigStatus } from "@/lib/config";

type StepKey = "business" | "openai" | "smtp" | "slack";
const STEPS: { key: StepKey; title: string }[] = [
  { key: "business", title: "Business" },
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
    business: initialStatus.business,
    openai: initialStatus.openai,
    smtp: initialStatus.smtp,
    slack: initialStatus.slack,
  });
  const firstUnfinished = STEPS.findIndex((s) => !saved[s.key]);
  const [activeIndex, setActiveIndex] = useState(
    firstUnfinished === -1 ? STEPS.length - 1 : firstUnfinished
  );

  const allDone = saved.business && saved.openai && saved.smtp && saved.slack;
  const active = STEPS[activeIndex];

  function markSaved(key: StepKey) {
    setSaved((prev) => ({ ...prev, [key]: true }));
  }

  return (
    <main className="mx-auto min-h-screen max-w-lg px-4 py-12">
      <h1 className="mb-1 text-2xl font-semibold">Setup</h1>
      <p className="mb-6 text-sm text-slate-600 dark:text-slate-400">
        Connect the services the lead pipeline needs. Each step explains what
        the fields mean and where to find the values -- steps that call a
        real service must pass a live test before you can move on.
      </p>

      <ol className="mb-8 flex gap-2">
        {STEPS.map((step, i) => (
          <li key={step.key} className="flex-1">
            <button
              type="button"
              onClick={() => setActiveIndex(i)}
              className={`w-full rounded-md border px-2 py-2 text-center text-sm transition ${
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

      {active.key === "business" && (
        <BusinessStep saved={saved.business} onSaved={() => markSaved("business")} />
      )}
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
  submitLabel = "Test & Save",
}: {
  saved: boolean;
  children: React.ReactNode;
  onSubmit: (e: FormEvent<HTMLFormElement>) => void;
  submitting: boolean;
  error: string | null;
  submitLabel?: string;
}) {
  return (
    <form onSubmit={onSubmit} className="space-y-4 rounded-lg border border-slate-200 p-4 dark:border-slate-800">
      {children}
      {error && (
        <p className="rounded-md bg-red-50 p-2 text-sm text-red-700 dark:bg-red-950 dark:text-red-300">
          {error}
        </p>
      )}
      {saved && !error && (
        <p className="text-sm text-emerald-600 dark:text-emerald-400">Verified and saved.</p>
      )}
      <button
        type="submit"
        disabled={submitting}
        className="rounded-md bg-slate-900 px-4 py-2 text-sm font-medium text-white disabled:opacity-60 dark:bg-slate-100 dark:text-slate-900"
      >
        {submitting ? "Testing..." : submitLabel}
      </button>
    </form>
  );
}

function Input({
  label,
  hint,
  ...props
}: React.InputHTMLAttributes<HTMLInputElement> & { label: string; hint?: React.ReactNode }) {
  return (
    <div>
      <label className="mb-1 block text-sm font-medium">{label}</label>
      {hint && (
        <p className="mb-1 text-xs text-slate-500 dark:text-slate-400">{hint}</p>
      )}
      <input
        {...props}
        className="w-full rounded-md border border-slate-300 bg-white px-3 py-2 text-sm outline-none focus:border-slate-500 dark:border-slate-700 dark:bg-slate-900"
      />
    </div>
  );
}

function BusinessStep({ saved, onSaved }: { saved: boolean; onSaved: () => void }) {
  const [submitting, setSubmitting] = useState(false);
  const [error, setError] = useState<string | null>(null);

  async function handleSubmit(e: FormEvent<HTMLFormElement>) {
    e.preventDefault();
    setSubmitting(true);
    setError(null);
    const data = Object.fromEntries(new FormData(e.currentTarget).entries());
    try {
      await saveConfig("business", {
        company_name: data.company_name,
        sender_name: data.sender_name || null,
      });
      onSaved();
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to save business info.");
    } finally {
      setSubmitting(false);
    }
  }

  return (
    <StepShell saved={saved} onSubmit={handleSubmit} submitting={submitting} error={error} submitLabel="Save">
      <p className="text-sm text-slate-600 dark:text-slate-400">
        This is your business, not the lead&apos;s. It&apos;s used to sign
        drafted emails properly instead of leaving a placeholder like{" "}
        <code>[Your Name]</code>. Nothing here is tested against an outside
        service -- just saved.
      </p>
      <Input
        label="Company name"
        name="company_name"
        required
        placeholder="Acme Corp"
        hint="Shown in the email signature, e.g. &quot;Best, the Acme Corp team&quot;."
      />
      <Input
        label="Sender name (optional)"
        name="sender_name"
        placeholder="Jane from Acme Corp"
        hint="If you leave this blank, the company name above is used instead. Fill it in if a specific person should sign the emails."
      />
    </StepShell>
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
      <div className="text-sm text-slate-600 dark:text-slate-400">
        <p className="mb-1">
          Used to summarize the lead&apos;s website and draft the outreach
          email. Get a key at{" "}
          <a
            href="https://platform.openai.com/api-keys"
            target="_blank"
            rel="noreferrer"
            className="underline"
          >
            platform.openai.com/api-keys
          </a>{" "}
          (log in → &quot;Create new secret key&quot;).
        </p>
        <p>
          Note: OpenAI requires a payment method on the account before API
          calls work, even for small usage -- add one at{" "}
          <a
            href="https://platform.openai.com/settings/organization/billing/overview"
            target="_blank"
            rel="noreferrer"
            className="underline"
          >
            platform.openai.com/settings/organization/billing
          </a>{" "}
          if the test below fails with a quota/billing error.
        </p>
      </div>
      <Input
        label="OpenAI API key"
        name="api_key"
        type="password"
        required
        placeholder="sk-..."
        hint="Starts with sk-. Treat it like a password -- it's encrypted at rest, never shown again after you paste it here."
      />
    </StepShell>
  );
}

const SMTP_PRESETS = [
  { name: "Gmail", host: "smtp.gmail.com", port: 587 },
  { name: "Outlook / Microsoft 365", host: "smtp.office365.com", port: 587 },
  { name: "Yahoo", host: "smtp.mail.yahoo.com", port: 587 },
  { name: "Zoho", host: "smtp.zoho.com", port: 587 },
];

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
      <div className="text-sm text-slate-600 dark:text-slate-400">
        <p className="mb-2">
          This is the email account that actually sends the approved outreach
          email -- fill in the fields below with the details of whichever
          inbox you want emails to come from.
        </p>
        <p className="mb-1 font-medium text-slate-700 dark:text-slate-300">
          Common host / port values:
        </p>
        <ul className="ml-4 list-disc space-y-0.5">
          {SMTP_PRESETS.map((p) => (
            <li key={p.name}>
              {p.name}: <code>{p.host}</code>, port <code>{p.port}</code>
            </li>
          ))}
        </ul>
      </div>

      <Input
        label="SMTP host"
        name="host"
        required
        placeholder="smtp.gmail.com"
        hint="Your email provider's outgoing mail server -- see the list above, or check your provider's SMTP settings page."
      />
      <Input
        label="Port"
        name="port"
        type="number"
        required
        defaultValue={587}
        hint="587 works for almost every provider (including everything listed above). Use 465 only if your provider specifically requires SSL."
      />
      <Input
        label="Username"
        name="username"
        required
        placeholder="you@yourcompany.com"
        hint="Almost always your full email address, not just the part before the @."
      />
      <Input
        label="Password"
        name="password"
        type="password"
        required
        hint={
          <>
            For Gmail, this must be a 16-character{" "}
            <a
              href="https://myaccount.google.com/apppasswords"
              target="_blank"
              rel="noreferrer"
              className="underline"
            >
              App Password
            </a>{" "}
            -- your normal Google password will not work. App Passwords
            require 2-Step Verification to be turned on for the account
            first. Other providers may also require an app-specific password
            instead of your regular one.
          </>
        }
      />
      <Input
        label="From address"
        name="from_address"
        type="email"
        required
        placeholder="you@yourcompany.com"
        hint="The address leads will see as the sender. Should normally match Username above."
      />
      <Input
        label="Send a test email to"
        name="test_recipient"
        type="email"
        required
        placeholder="a-different-inbox@example.com"
        hint="Where the test email is delivered so you can confirm it worked. Using a different inbox than From address makes it easier to tell the test actually arrived."
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
        <p className="mb-1">
          Drafted emails are posted here with Approve / Reject buttons before
          anything is sent. Setup:
        </p>
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
            </a>{" "}
            → &quot;Create New App&quot; → &quot;From scratch&quot;
          </li>
          <li>
            In the left sidebar, open <strong>OAuth &amp; Permissions</strong>
          </li>
          <li>
            Scroll to <strong>Scopes → Bot Token Scopes</strong> and add{" "}
            <code>chat:write</code>
          </li>
          <li>
            Scroll up and click <strong>Install to Workspace</strong>, then
            allow it
          </li>
          <li>
            Copy the <strong>Bot User OAuth Token</strong> shown at the top
            of that page (starts with <code>xoxb-</code>)
          </li>
          <li>
            In Slack, go to the channel you want approvals posted to and
            type <code>/invite @your-app-name</code> so the bot can post
            there
          </li>
        </ol>
      </div>
      <Input
        label="Bot User OAuth token"
        name="bot_token"
        type="password"
        required
        placeholder="xoxb-..."
        hint="From the OAuth & Permissions page, step 5 above."
      />
      <Input
        label="Channel"
        name="channel"
        required
        placeholder="#new-leads"
        hint="The channel name (e.g. #new-leads) or channel ID. The bot must be invited to it first (step 6 above), or the test below will fail."
      />
    </StepShell>
  );
}
