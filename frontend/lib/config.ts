import "server-only";

// Server-only env vars: never sent to the browser bundle.
const BACKEND_URL = process.env.BACKEND_URL ?? "http://backend:8000";
const SETUP_TOKEN = process.env.SETUP_TOKEN ?? "";
// Internal n8n origin, used only to resume the Wait-node webhook server-side
// from /approval -- never exposed to the browser. See lib/approval.ts.
export const N8N_BASE_URL = process.env.N8N_BASE_URL ?? "http://n8n:5678";

export type ConfigStatus = {
  openai: boolean;
  smtp: boolean;
  slack: boolean;
  business: boolean;
  branding: boolean;
  fully_configured: boolean;
};

export type SocialLink = {
  label: string;
  url: string;
};

export type Branding = {
  primary_color: string;
  accent_color: string;
  background_color: string;
  text_color: string;
  logo_url: string;
  font_family: "sans" | "serif" | "mono" | "rounded";
  brand_tone: "professional" | "friendly" | "bold" | "minimal" | "luxury";
  industry: string;
  description: string;
  value_proposition: string;
  cta_label: string;
  cta_url: string;
  sender_title: string;
  sender_phone: string;
  website_url: string;
  tagline: string;
  address: string;
  social_links: SocialLink[];
  unsubscribe_line: string;
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

/**
 * Server-to-server read of the current branding config (or neutral
 * defaults, if nothing has been saved yet). Branding holds no secrets, so
 * unlike the other sections it's safe to read back and used to pre-fill
 * the wizard step instead of forcing a blank re-entry every visit.
 */
export async function getBranding(): Promise<Branding> {
  const res = await fetch(`${BACKEND_URL}/config/branding`, {
    headers: { "X-Setup-Token": SETUP_TOKEN },
    cache: "no-store",
  });
  if (!res.ok) {
    throw new Error(`Failed to load branding: ${res.status}`);
  }
  return res.json();
}
