// Token-attaching fetch wrapper.
//
// Behavior:
// - Acquires an Entra access token via MSAL (or `stub-token` under ?fakeAuth=1).
// - Sets `Authorization: Bearer <token>`.
// - On 401, retries ONCE with a forced silent refresh.
// - If the second 401 carries `{ "detail": "consent_required", "claims": "..." }`,
//   triggers an interactive popup with the claims challenge (Phase 3 Finding 5).
// - On persistent 401, redirects to login.
//
// Bodies: callers MUST pass string or BodyInit forms that can be re-sent. The
// wrapper does not clone ReadableStream bodies; passing one risks a second-pass
// "body already consumed" error.

import { pca, popupRequest } from './msal-config';
import { acquireToken } from './use-account';

export class ApiError extends Error {
  status: number;
  body: unknown;
  constructor(status: number, body: unknown, message?: string) {
    super(message ?? `API error ${status}`);
    this.status = status;
    this.body = body;
  }
}

const API_BASE = import.meta.env.VITE_API_BASE ?? '';

export async function apiFetch(path: string, opts: RequestInit = {}): Promise<Response> {
  const url = `${API_BASE}${path}`;
  const token = await acquireToken();
  const headers = new Headers(opts.headers);
  headers.set('Authorization', `Bearer ${token}`);

  let res = await fetch(url, { ...opts, headers });
  if (res.status !== 401) return res;

  // First 401 — try a forced silent refresh.
  // Clone the body if the caller gave us a Request; for plain RequestInit
  // strings/Blobs/etc. fetch happily re-sends them.
  const body = opts.body;
  const fresh = await acquireToken({ forceRefresh: true });
  headers.set('Authorization', `Bearer ${fresh}`);
  res = await fetch(url, { ...opts, body, headers });
  if (res.status !== 401) return res;

  // Second 401 — check for a claims challenge.
  let parsed: { detail?: string; claims?: string } | null = null;
  try {
    parsed = (await res.clone().json()) as { detail?: string; claims?: string };
  } catch {
    parsed = null;
  }
  if (parsed?.detail === 'consent_required' && parsed.claims) {
    const challenged = await acquireToken({ claims: parsed.claims });
    headers.set('Authorization', `Bearer ${challenged}`);
    return fetch(url, { ...opts, body, headers });
  }

  // True session expiry — redirect to login.
  await redirectToLogin();
  return res;
}

export async function apiJson<T>(path: string, opts: RequestInit = {}): Promise<T> {
  const res = await apiFetch(path, opts);
  const text = await res.text();
  const data = text ? JSON.parse(text) : null;
  if (!res.ok) {
    throw new ApiError(res.status, data, `${path} → ${res.status}`);
  }
  return data as T;
}

async function redirectToLogin(): Promise<void> {
  await pca.loginPopup(popupRequest);
}
