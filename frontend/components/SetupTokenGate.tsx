export default function SetupTokenGate({ hasError }: { hasError: boolean }) {
  return (
    <main className="mx-auto flex min-h-screen max-w-sm flex-col justify-center px-4">
      <h1 className="mb-2 text-xl font-semibold">Setup access</h1>
      <p className="mb-4 text-sm text-slate-600 dark:text-slate-400">
        Enter the <code>SETUP_TOKEN</code> value from your <code>.env</code> file to
        continue.
      </p>
      <form action="/api/setup/authorize" method="POST" className="space-y-3">
        <input
          type="password"
          name="token"
          required
          autoFocus
          placeholder="Setup token"
          className="w-full rounded-md border border-slate-300 bg-white px-3 py-2 text-sm outline-none focus:border-slate-500 dark:border-slate-700 dark:bg-slate-900"
        />
        {hasError && (
          <p className="text-sm text-red-600 dark:text-red-400">
            That token doesn&apos;t match SETUP_TOKEN in your .env.
          </p>
        )}
        <button
          type="submit"
          className="w-full rounded-md bg-slate-900 px-4 py-2 text-sm font-medium text-white transition hover:bg-slate-700 dark:bg-slate-100 dark:text-slate-900 dark:hover:bg-white"
        >
          Continue
        </button>
      </form>
    </main>
  );
}
