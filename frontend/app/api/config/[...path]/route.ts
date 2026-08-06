import { NextRequest, NextResponse } from "next/server";
import { isSetupAuthorized } from "@/lib/auth";

const BACKEND_URL = process.env.BACKEND_URL ?? "http://backend:8000";
const SETUP_TOKEN = process.env.SETUP_TOKEN ?? "";

async function proxy(req: NextRequest, path: string[]) {
  if (!(await isSetupAuthorized())) {
    return NextResponse.json({ error: "Not authorized" }, { status: 401 });
  }

  const target = `${BACKEND_URL}/config/${path.join("/")}`;
  const init: RequestInit = {
    method: req.method,
    headers: { "Content-Type": "application/json", "X-Setup-Token": SETUP_TOKEN },
  };
  if (req.method !== "GET" && req.method !== "HEAD") {
    init.body = await req.text();
  }

  const upstream = await fetch(target, init);
  const data = await upstream.text();
  return new NextResponse(data, {
    status: upstream.status,
    headers: { "Content-Type": upstream.headers.get("Content-Type") ?? "application/json" },
  });
}

export async function GET(
  req: NextRequest,
  { params }: { params: Promise<{ path: string[] }> }
) {
  return proxy(req, (await params).path);
}

export async function POST(
  req: NextRequest,
  { params }: { params: Promise<{ path: string[] }> }
) {
  return proxy(req, (await params).path);
}
