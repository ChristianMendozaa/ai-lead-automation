import "server-only";

// Server-only env vars: never sent to the browser bundle.
const BACKEND_URL = process.env.BACKEND_URL ?? "http://backend:8000";
const SETUP_TOKEN = process.env.SETUP_TOKEN ?? "";

export type ConfigStatus = {
  openai: boolean;
  smtp: boolean;
  slack: boolean;
  fully_configured: boolean;
};

/**
 * Server-to-server call to the backend's /config/status, using the real
 * shared secret directly (this never touches the browser). Used both to
 * decide whether "/" should redirect to "/setup", and to render the
 * wizard's initial step state.
 */
export async function getConfigStatus(): Promise<ConfigStatus> {
  const res = await fetch(`${BACKEND_URL}/config/status`, {
    headers: { "X-Setup-Token": SETUP_TOKEN },
    cache: "no-store",
  });
  if (!res.ok) {
    throw new Error(`Failed to load config status: ${res.status}`);
  }
  return res.json();
}
