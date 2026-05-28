import { StrictMode } from 'react';
import { createRoot } from 'react-dom/client';
import { MsalProvider } from '@azure/msal-react';

import '@ds/styles/tokens.css';
import './styles/app-chrome.css';
import './styles/app-responsive.css';
import { AppRoot } from './app-root';
import { msalReady, pca } from './auth';
import { AppStateProvider } from './state/app-state-context';

const rootEl = document.getElementById('root');
if (!rootEl) throw new Error('Root element #root not found');

// MSAL v3+ requires explicit init before first call. We wait once at boot so
// all downstream hooks/components can rely on the cache being ready.
msalReady.then(() => {
  createRoot(rootEl).render(
    <StrictMode>
      <MsalProvider instance={pca}>
        <AppStateProvider>
          <AppRoot />
        </AppStateProvider>
      </MsalProvider>
    </StrictMode>,
  );
});
