import { StrictMode } from 'react';
import { createRoot } from 'react-dom/client';

import './styles/tokens.css';
import './styles/design-system-chrome.css';
import { DesignSystemApp } from './design-system-app';

const rootEl = document.getElementById('root');
if (!rootEl) throw new Error('Root element #root not found');

createRoot(rootEl).render(
  <StrictMode>
    <DesignSystemApp />
  </StrictMode>,
);
