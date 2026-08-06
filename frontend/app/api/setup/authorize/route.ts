import { NextRequest, NextResponse } from "next/server";
import { setSetupSessionCookie } from "@/lib/auth";

export async function POST(req: NextRequest) {
  const form = await req.formData();
  const token = String(form.get("token") ?? "");
  const ok = await setSetupSessionCookie(token);

  const url = new URL("/setup", req.url);
  if (!ok) url.searchParams.set("error", "1");
  return NextResponse.redirect(url, { status: 303 });
}
