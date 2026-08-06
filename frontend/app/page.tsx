import { redirect } from "next/navigation";
import LeadForm from "@/components/LeadForm";
import { getConfigStatus } from "@/lib/config";

// Config state can change at any time via /setup, so always check fresh.
export const dynamic = "force-dynamic";

export default async function HomePage() {
  const status = await getConfigStatus();
  if (!status.fully_configured) {
    redirect("/setup");
  }

  return (
    <main className="mx-auto flex min-h-screen max-w-md flex-col justify-center px-4 py-16">
      <h1 className="mb-1 text-2xl font-semibold">Get in touch</h1>
      <p className="mb-6 text-sm text-slate-600 dark:text-slate-400">
        Tell us a bit about you and we&apos;ll follow up soon.
      </p>
      <LeadForm />
    </main>
  );
}
