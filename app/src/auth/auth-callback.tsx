// Callback route landing for MSAL's loginRedirect.
//
// By the time React renders this component, `handleRedirectPromise` has
// already run in main.tsx — the URL fragment (#code=…) is consumed and
// MSAL's account cache is populated. We just navigate back home; the
// `useActiveAccount()` hook will report authenticated on the next render.
//
// Do NOT call `location.reload()` here — it would risk re-entering the
// callback path before history.replaceState flushes, and it wipes
// in-memory state (router, app-state context).

import { Navigate } from 'react-router-dom';

export function AuthCallback() {
  return <Navigate to="/" replace />;
}
