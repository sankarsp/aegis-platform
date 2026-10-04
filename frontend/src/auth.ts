/**
 * Sign-in with the Amazon Cognito hosted UI (authorization code flow with PKCE).
 * Enabled when VITE_COGNITO_DOMAIN and VITE_COGNITO_CLIENT_ID are set at build time;
 * otherwise the app runs in local dev mode and the API uses its dev user.
 */
const DOMAIN = import.meta.env.VITE_COGNITO_DOMAIN as string | undefined; // e.g. https://aegis-demo.auth.us-east-1.amazoncognito.com
const CLIENT_ID = import.meta.env.VITE_COGNITO_CLIENT_ID as string | undefined;
const REDIRECT = `${window.location.origin}/`;
const KEY = "aegis.idToken";

export const authEnabled = Boolean(DOMAIN && CLIENT_ID);
let idToken: string | null = null;

const b64url = (bytes: ArrayBuffer) =>
  btoa(String.fromCharCode(...new Uint8Array(bytes))).replace(/\+/g, "-").replace(/\//g, "_").replace(/=+$/, "");

function expired(token: string): boolean {
  try {
    const payload = JSON.parse(atob(token.split(".")[1].replace(/-/g, "+").replace(/_/g, "/")));
    return payload.exp * 1000 < Date.now() + 30_000;
  } catch {
    return true;
  }
}

async function redirectToSignIn(): Promise<never> {
  const verifier = b64url(crypto.getRandomValues(new Uint8Array(32)).buffer);
  const challenge = b64url(await crypto.subtle.digest("SHA-256", new TextEncoder().encode(verifier)));
  const state = b64url(crypto.getRandomValues(new Uint8Array(16)).buffer);
  sessionStorage.setItem("aegis.pkce", JSON.stringify({ verifier, state, path: location.pathname + location.search }));
  const q = new URLSearchParams({
    response_type: "code", client_id: CLIENT_ID!, redirect_uri: REDIRECT, scope: "openid email profile",
    code_challenge_method: "S256", code_challenge: challenge, state,
  });
  window.location.assign(`${DOMAIN}/oauth2/authorize?${q}`);
  return new Promise<never>(() => {});
}

/** Call once before rendering. Completes a sign-in redirect or starts one. */
export async function initAuth(): Promise<void> {
  if (!authEnabled) return;
  const params = new URLSearchParams(location.search);
  const code = params.get("code");
  if (code) {
    const saved = JSON.parse(sessionStorage.getItem("aegis.pkce") ?? "{}");
    if (saved.state !== params.get("state")) throw new Error("Sign-in failed a security check. Reload to try again.");
    const res = await fetch(`${DOMAIN}/oauth2/token`, {
      method: "POST",
      headers: { "Content-Type": "application/x-www-form-urlencoded" },
      body: new URLSearchParams({ grant_type: "authorization_code", client_id: CLIENT_ID!, code, redirect_uri: REDIRECT, code_verifier: saved.verifier }),
    });
    if (!res.ok) throw new Error("Sign-in could not be completed. Reload to try again.");
    const tokens = await res.json();
    idToken = tokens.id_token;
    sessionStorage.setItem(KEY, tokens.id_token);
    sessionStorage.removeItem("aegis.pkce");
    history.replaceState(null, "", saved.path || "/");
    return;
  }
  idToken = sessionStorage.getItem(KEY);
  if (!idToken || expired(idToken)) await redirectToSignIn();
}

export async function authHeader(): Promise<Record<string, string>> {
  if (!authEnabled) return {};
  if (!idToken || expired(idToken)) await redirectToSignIn();
  return { Authorization: `Bearer ${idToken}` };
}

export function signOut() {
  sessionStorage.removeItem(KEY);
  idToken = null;
  if (authEnabled) window.location.assign(`${DOMAIN}/logout?${new URLSearchParams({ client_id: CLIENT_ID!, logout_uri: REDIRECT })}`);
}
