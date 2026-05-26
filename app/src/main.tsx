import { StrictMode } from 'react';
import { createRoot } from 'react-dom/client';

import '@ds/styles/tokens.css';
import './styles/app-chrome.css';
import './styles/app-responsive.css';
import { AppRoot } from './app-root';
import { AppStateProvider } from './state/app-state-context';

const rootEl = document.getElementById('root');
if (!rootEl) throw new Error('Root element #root not found');

createRoot(rootEl).render(
  <StrictMode>
    <AppStateProvider>
      <AppRoot />
    </AppStateProvider>
  </StrictMode>,
);
