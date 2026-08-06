import { NextRequest, NextResponse } from "next/server";

// Server-only: the n8n webhook URL never reaches the browser, and n8n's
// port doesn't need to be exposed publicly for this to work.
const N8N_WEBHOOK_URL =
  process.env.N8N_WEBHOOK_URL ?? "http://n8n:5678/webhook/lead-intake";

export async function POST(req: NextRequest) {
  let body: Record<string, unknown>;
  try {
    body = await req.json();
  } catch {
    return NextResponse.json({ error: "Invalid JSON body" }, { status: 400 });
  }

  // Honeypot: bots that fill in every field (including the hidden one)
  // get a fake success response so we don't tip them off.
  if (typeof body.hp_field === "string" && body.hp_field.trim() !== "") {
    return NextResponse.json({ ok: true });
  }
  delete body.hp_field;

  if (typeof body.name !== "string" || typeof body.email !== "string") {
    return NextResponse.json(
      { error: "name and email are required" },
      { status: 422 }
    );
  }

  try {
    const upstream = await fetch(N8N_WEBHOOK_URL, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(body),
      // The n8n webhook responds immediately (before the pipeline finishes),
      // so this should return fast.
      signal: AbortSignal.timeout(15_000),
    });
    if (!upstream.ok) {
      return NextResponse.json(
        { error: "Upstream pipeline rejected the submission" },
        { status: 502 }
      );
    }
  } catch {
    return NextResponse.json(
      { error: "Could not reach the lead pipeline" },
      { status: 502 }
    );
  }

  return NextResponse.json({ ok: true });
}
