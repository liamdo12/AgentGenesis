import { StrictMode } from 'react';
import { createRoot } from 'react-dom/client';
import { MsalProvider } from '@azure/msal-react';
import { RouterProvider } from 'react-router-dom';

import '@ds/styles/tokens.css';
import './styles/app-chrome.css';
import './styles/app-responsive.css';
import { msalReady, pca } from './auth';
import { AuthErrorBanner } from './auth/auth-error-banner';
import { router } from './router';
import { AppStateProvider } from './state/app-state-context';

const HANDLE_REDIRECT_TIMEOUT_MS = 10_000;

function getRoot(): HTMLElement {
  const el = document.getElementById('root');
  if (!el) throw new Error('Root element #root not found');
  return el;
}

// MSAL v3+ requires explicit init before first call. handleRedirectPromise()
// then consumes any post-login URL fragment so downstream components can
// rely on the account cache being ready. Wrap in try/catch + timeout so
// transient AAD errors (network, interaction_in_progress, stale state)
// don't strand the user on a blank page.
async function boot() {
  let bootError: Error | null = null;
  try {
    await msalReady;
    await Promise.race([
      pca.handleRedirectPromise(),
      new Promise<never>((_, reject) =>
        setTimeout(
          () => reject(new Error('msal_handleRedirect_timeout')),
          HANDLE_REDIRECT_TIMEOUT_MS,
        ),
      ),
    ]);
  } catch (e) {
    bootError = e instanceof Error ? e : new Error(String(e));
    // Best-effort clear; clearCache itself can throw if MSAL never init'd.
    try {
      await pca.clearCache();
    } catch {
      /* swallow */
    }
    // eslint-disable-next-line no-console
    console.error('MSAL boot error:', bootError);
  }

  createRoot(getRoot()).render(
    <StrictMode>
      <MsalProvider instance={pca}>
        <AppStateProvider>
          {bootError && <AuthErrorBanner error={bootError} />}
          <RouterProvider router={router} />
        </AppStateProvider>
      </MsalProvider>
    </StrictMode>,
  );
}

void boot();
