import "server-only";

import { N8N_BASE_URL } from "./config";

export type ApprovalResult =
  | { kind: "approved" }
  | { kind: "rejected" }
  | { kind: "already-used" }
  | { kind: "invalid"; reason: string }
  | { kind: "error"; reason: string };

/**
 * Resumes n8n's per-execution Wait-node webhook server-side, so the
 * approver's browser only ever sees our own /approval page -- never n8n's
 * raw JSON response, and never needs network access to n8n at all.
 *
 * `rawResumeUrl` comes straight from the page's query string, so it is
 * untrusted input: without the origin/path allowlist below, this function
 * would be an open SSRF pivot into the Docker network (anything reachable
 * from the frontend container, including the backend's unauthenticated
 * internal routes).
 */
export async function resumeApproval(rawResumeUrl: string): Promise<ApprovalResult> {
  let url: URL;
  try {
    url = new URL(rawResumeUrl);
  } catch {
    return { kind: "invalid", reason: "Malformed approval link." };
  }

  const n8nOrigin = new URL(N8N_BASE_URL).origin;
  if (url.origin !== n8nOrigin || !url.pathname.startsWith("/webhook-waiting/")) {
    return { kind: "invalid", reason: "This link doesn't point at a known approval webhook." };
  }

  const decision = url.searchParams.get("decision");
  if (decision !== "approve" && decision !== "reject") {
    return { kind: "invalid", reason: "This link is missing a valid decision." };
  }

  try {
    const res = await fetch(url, {
      method: "GET",
      cache: "no-store",
      redirect: "manual",
      signal: AbortSignal.timeout(15_000),
    });

    // n8n returns 409 when this execution's wait already resumed (a
    // double-click, or the other button clicked first) and 404 once the
    // execution/webhook registration is gone entirely (e.g. the 7-day wait
    // window expired) -- one message covers both cases correctly.
    if (res.status === 404 || res.status === 409) {
      return { kind: "already-used" };
    }
    if (res.status >= 200 && res.status < 400) {
      return decision === "approve" ? { kind: "approved" } : { kind: "rejected" };
    }
    return { kind: "error", reason: `Approval webhook responded with ${res.status}.` };
  } catch {
    return { kind: "error", reason: "Could not reach the approval webhook." };
  }
}
