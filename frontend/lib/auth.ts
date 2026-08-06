import "server-only";
import { cookies } from "next/headers";

// Gates access to /setup and /api/config/*. There's no user-account system
// in v1 -- just a shared secret (SETUP_TOKEN from .env) that the deploying
// admin already knows before ever visiting /setup. Once entered, it's
// stashed in an httpOnly cookie so it never lands in client-side JS again.
const COOKIE_NAME = "la_setup_session";
const SETUP_TOKEN = process.env.SETUP_TOKEN ?? "";

export async function isSetupAuthorized(): Promise<boolean> {
  if (!SETUP_TOKEN) return false;
  const store = await cookies();
  return store.get(COOKIE_NAME)?.value === SETUP_TOKEN;
}

export async function setSetupSessionCookie(token: string): Promise<boolean> {
  if (!SETUP_TOKEN || token !== SETUP_TOKEN) return false;
  const store = await cookies();
  store.set(COOKIE_NAME, token, {
    httpOnly: true,
    sameSite: "lax",
    path: "/",
    maxAge: 60 * 60 * 24 * 30, // 30 days
  });
  return true;
}

export { COOKIE_NAME as SETUP_SESSION_COOKIE_NAME };
