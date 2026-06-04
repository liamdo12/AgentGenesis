// Surfaces MSAL boot errors with a recovery button.
//
// Mounted by main.tsx when `pca.handleRedirectPromise()` fails or times
// out — without this banner the user would see a blank app with no path
// forward. Common triggers: `interaction_in_progress` (stale MSAL state),
// `BrowserAuthError: hash_does_not_contain_known_properties` (bad
// callback URL), network failure during the redirect dance.
//
// Recovery: clicking Retry calls `pca.loginRedirect` directly. If the
// underlying cause is transient (network), this works. If it's a config
// error (Entra redirect URI mismatch), the next redirect will fail too
// and the banner re-renders.

import { pca, popupRequest } from './msal-config';

type Props = { error: Error };

export function AuthErrorBanner({ error }: Props) {
  const retry = async () => {
    try {
      await pca.loginRedirect(popupRequest);
    } catch {
      // pca.loginRedirect navigates the page on success; reaching here
      // means a synchronous failure (e.g. interaction_in_progress).
      // Reload to clear MSAL state and let main.tsx try again.
      window.location.reload();
    }
  };

  return (
    <div
      role="alert"
      style={{
        padding: '10px 16px',
        background: '#fff5f5',
        borderBottom: '1px solid var(--ag-danger, #e03131)',
        color: '#a61e1e',
        fontSize: 13,
        display: 'flex',
        gap: 12,
        alignItems: 'center',
      }}
    >
      <span style={{ flex: 1 }}>
        Sign-in didn&apos;t complete: <code>{error.message}</code>
      </span>
      <button
        type="button"
        onClick={retry}
        style={{
          padding: '4px 10px',
          background: 'var(--ag-danger, #e03131)',
          color: 'white',
          border: 0,
          borderRadius: 4,
          cursor: 'pointer',
          fontSize: 12,
        }}
      >
        Retry sign-in
      </button>
    </div>
  );
}
