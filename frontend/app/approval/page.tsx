import { resumeApproval, type ApprovalResult } from "@/lib/approval";
import { getBranding, type Branding } from "@/lib/config";

// The decision must be re-applied to n8n on every load (not cached), and
// the branding lookup below can change at any time via /setup.
export const dynamic = "force-dynamic";

export default async function ApprovalPage({
  searchParams,
}: {
  searchParams: Promise<{ resume?: string; lead?: string }>;
}) {
  const { resume, lead } = await searchParams;

  const result: ApprovalResult = resume
    ? await resumeApproval(resume)
    : { kind: "invalid", reason: "No approval link was provided." };

  // Branding is cosmetic only -- a failure to load it must never mask
  // whether the approval itself succeeded.
  let branding: Branding | null = null;
  try {
    branding = await getBranding();
  } catch {
    branding = null;
  }

  const { emoji, heading, detail } = copyFor(result, lead);
  const accent = branding?.primary_color || "#0f172a";

  return (
    <main className="mx-auto flex min-h-screen max-w-md flex-col items-center justify-center px-4 py-16 text-center">
      {branding?.logo_url && (
        // eslint-disable-next-line @next/next/no-img-element -- external, unknown-dimension branding asset
        <img src={branding.logo_url} alt="" className="mb-6 max-h-12 max-w-[200px] object-contain" />
      )}
      <div className="text-4xl">{emoji}</div>
      <h1 className="mt-4 text-xl font-semibold" style={{ color: accent }}>
        {heading}
      </h1>
      <p className="mt-2 text-sm text-slate-600 dark:text-slate-400">{detail}</p>
      {branding?.tagline && (
        <p className="mt-8 text-xs text-slate-400 dark:text-slate-600">{branding.tagline}</p>
      )}
    </main>
  );
}

function copyFor(
  result: ApprovalResult,
  lead: string | undefined
): { emoji: string; heading: string; detail: string } {
  const who = lead ? lead : "the lead";
  switch (result.kind) {
    case "approved":
      return {
        emoji: "✅",
        heading: "Approved",
        detail: `The outreach email is on its way to ${who}.`,
      };
    case "rejected":
      return {
        emoji: "❌",
        heading: "Rejected",
        detail: `No email will be sent to ${who}.`,
      };
    case "already-used":
      return {
        emoji: "⏳",
        heading: "Already handled",
        detail: "This approval link has already been used, or it has expired.",
      };
    case "invalid":
    case "error":
      return {
        emoji: "⚠️",
        heading: "Something went wrong",
        detail: result.reason,
      };
  }
}
