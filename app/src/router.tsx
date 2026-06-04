// Minimal router. v1 has only one non-default route — the MSAL callback.
// Every other path falls through to `<AppRoot>` so deep links don't 404.

import { createBrowserRouter } from 'react-router-dom';
import { AppRoot } from './app-root';
import { AuthCallback } from './auth/auth-callback';

export const router = createBrowserRouter([
  { path: '/auth/login/callback', element: <AuthCallback /> },
  { path: '*', element: <AppRoot /> },
]);
