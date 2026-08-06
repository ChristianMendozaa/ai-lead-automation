"use client";

import { FormEvent, useState } from "react";

type Status = "idle" | "submitting" | "success" | "error";

export default function LeadForm() {
  const [status, setStatus] = useState<Status>("idle");
  const [error, setError] = useState<string | null>(null);

  async function handleSubmit(e: FormEvent<HTMLFormElement>) {
    e.preventDefault();
    setStatus("submitting");
    setError(null);

    const form = e.currentTarget;
    const data = Object.fromEntries(new FormData(form).entries());

    try {
      const res = await fetch("/api/lead", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(data),
      });
      if (!res.ok) throw new Error(`Request failed (${res.status})`);
      setStatus("success");
      form.reset();
    } catch {
      setStatus("error");
      setError("Something went wrong sending your message. Please try again.");
    }
  }

  if (status === "success") {
    return (
      <div className="rounded-lg border border-emerald-300 bg-emerald-50 p-6 text-emerald-900 dark:border-emerald-700 dark:bg-emerald-950 dark:text-emerald-200">
        <p className="font-medium">Thanks — we got your message!</p>
        <p className="mt-1 text-sm opacity-80">
          Someone from our team will be in touch shortly.
        </p>
      </div>
    );
  }

  return (
    <form onSubmit={handleSubmit} className="space-y-4">
      {/* Honeypot: hidden from real users via CSS, bots that fill every
          field will trip it. The API route silently drops submissions
          where this is non-empty. */}
      <div className="absolute left-[-9999px] opacity-0" aria-hidden="true">
        <label htmlFor="hp_field">Leave this field empty</label>
        <input id="hp_field" name="hp_field" type="text" tabIndex={-1} autoComplete="off" />
      </div>

      <Field label="Name" name="name" required />
      <Field label="Email" name="email" type="email" required />
      <Field label="Phone" name="phone" type="tel" />
      <Field label="Company" name="company" />
      <Field
        label="Company website"
        name="website"
        type="text"
        placeholder="acme.com"
      />
      <div>
        <label htmlFor="message" className="mb-1 block text-sm font-medium">
          Message
        </label>
        <textarea
          id="message"
          name="message"
          rows={4}
          className="w-full rounded-md border border-slate-300 bg-white px-3 py-2 text-sm outline-none focus:border-slate-500 dark:border-slate-700 dark:bg-slate-900"
        />
      </div>

      {status === "error" && (
        <p className="text-sm text-red-600 dark:text-red-400">{error}</p>
      )}

      <button
        type="submit"
        disabled={status === "submitting"}
        className="w-full rounded-md bg-slate-900 px-4 py-2 text-sm font-medium text-white transition hover:bg-slate-700 disabled:opacity-60 dark:bg-slate-100 dark:text-slate-900 dark:hover:bg-white"
      >
        {status === "submitting" ? "Sending..." : "Send"}
      </button>
    </form>
  );
}

function Field({
  label,
  name,
  type = "text",
  required = false,
  placeholder,
}: {
  label: string;
  name: string;
  type?: string;
  required?: boolean;
  placeholder?: string;
}) {
  return (
    <div>
      <label htmlFor={name} className="mb-1 block text-sm font-medium">
        {label}
        {required && <span className="text-red-500"> *</span>}
      </label>
      <input
        id={name}
        name={name}
        type={type}
        required={required}
        placeholder={placeholder}
        className="w-full rounded-md border border-slate-300 bg-white px-3 py-2 text-sm outline-none focus:border-slate-500 dark:border-slate-700 dark:bg-slate-900"
      />
    </div>
  );
}
