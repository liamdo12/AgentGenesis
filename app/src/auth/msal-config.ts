// MSAL configuration. Singleton `pca` is exported so the React provider AND
// the imperative `apiFetch` helper share the same account cache.
//
// Scope shape per red-team Finding 5: `api://agentgenesis-api/access_as_user`
// (App ID URI), NOT `api://<client_id>/access_as_user`. Phase 1 pins the
// former in the Entra app manifest.

import { PublicClientApplication, type Configuration, type PopupRequest } from '@azure/msal-browser';

const tenant = import.meta.env.VITE_ENTRA_TENANT_ID || 'common';
const clientId = import.meta.env.VITE_ENTRA_CLIENT_ID || '00000000-0000-0000-0000-000000000000';

export const msalConfig: Configuration = {
  auth: {
    clientId,
    authority: `https://login.microsoftonline.com/${tenant}`,
    // SPA flow uses a dedicated callback route so MSAL has somewhere
    // explicit to land. The Entra app reg must list this exact URI under
    // its Single-page application platform.
    redirectUri: `${window.location.origin}/auth/login/callback`,
    // Logout still lands at origin; no `/auth/logout/callback` registered.
    postLogoutRedirectUri: window.location.origin,
  },
  // sessionStorage minimizes XSS exposure compared to localStorage. Per plan
  // "Risk surface — Frontend stores token".
  cache: { cacheLocation: 'sessionStorage' },
};

export const apiScopes = ['api://agentgenesis-api/access_as_user'];

export const popupRequest: PopupRequest = {
  scopes: apiScopes,
  prompt: 'select_account',
};

export const pca = new PublicClientApplication(msalConfig);

// MSAL v3+ requires explicit initialization before first call.
export const msalReady = pca.initialize();
