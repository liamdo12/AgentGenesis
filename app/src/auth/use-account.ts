// Account hook + token acquisition. The `?fakeAuth=1` branch is build-stripped
// in production by checking `import.meta.env.MODE` — Vite tree-shakes the dead
// branch out of the bundle. Per red-team Finding 6.

import { useCallback } from 'react';
import { useAccount, useIsAuthenticated, useMsal } from '@azure/msal-react';
import { InteractionRequiredAuthError, type AccountInfo } from '@azure/msal-browser';

import { apiScopes, pca, popupRequest } from './msal-config';

const FAKE_AUTH_ACCOUNT: AccountInfo = {
  homeAccountId: 'fake.fake',
  environment: 'fake',
  tenantId: 'stub-tenant',
  username: 'stub@example.com',
  localAccountId: 'stub-user',
  name: 'Stub User',
};

const FAKE_AUTH_TOKEN = 'stub-token';

export function fakeAuthEnabled(): boolean {
  if (import.meta.env.MODE === 'production') return false;
  return new URLSearchParams(window.location.search).get('fakeAuth') === '1';
}

export type ActiveAccount = { account: AccountInfo; isFake: boolean } | null;

export function useActiveAccount(): {
  active: ActiveAccount;
  isAuthenticated: boolean;
  login: () => Promise<void>;
  logout: () => Promise<void>;
} {
  const { instance } = useMsal();
  const account = useAccount();
  const realAuth = useIsAuthenticated();

  const isFake = fakeAuthEnabled();
  const isAuthenticated = isFake || realAuth;
  const active: ActiveAccount = isFake
    ? { account: FAKE_AUTH_ACCOUNT, isFake: true }
    : account
    ? { account, isFake: false }
    : null;

  const login = useCallback(async () => {
    if (isFake) return;
    await instance.loginPopup(popupRequest);
  }, [instance, isFake]);

  const logout = useCallback(async () => {
    if (isFake) {
      const u = new URL(window.location.href);
      u.searchParams.delete('fakeAuth');
      window.location.href = u.toString();
      return;
    }
    await instance.logoutPopup();
  }, [instance, isFake]);

  return { active, isAuthenticated, login, logout };
}

// Imperative token acquisition, used by `apiFetch`. Lives next to the MSAL
// instance singleton so its account state mirrors the React provider's.
export async function acquireToken(opts: { forceRefresh?: boolean; claims?: string } = {}): Promise<string> {
  if (fakeAuthEnabled()) return FAKE_AUTH_TOKEN;

  const account = pca.getActiveAccount() ?? pca.getAllAccounts()[0];
  if (!account) {
    const result = await pca.acquireTokenPopup({ ...popupRequest, claims: opts.claims });
    return result.accessToken;
  }
  try {
    const result = await pca.acquireTokenSilent({
      scopes: apiScopes,
      account,
      forceRefresh: opts.forceRefresh ?? false,
      claims: opts.claims,
    });
    return result.accessToken;
  } catch (e) {
    if (e instanceof InteractionRequiredAuthError) {
      const result = await pca.acquireTokenPopup({ ...popupRequest, claims: opts.claims });
      return result.accessToken;
    }
    throw e;
  }
}
