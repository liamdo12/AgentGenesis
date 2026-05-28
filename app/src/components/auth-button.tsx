import { useState } from 'react';
import { Icon } from '@ds/lib/icons';
import { useActiveAccount } from '../auth';

export function AuthButton() {
  const { active, isAuthenticated, login, logout } = useActiveAccount();
  const [busy, setBusy] = useState(false);
  const [menuOpen, setMenuOpen] = useState(false);

  const handle = async (fn: () => Promise<void>) => {
    setBusy(true);
    try {
      await fn();
    } finally {
      setBusy(false);
      setMenuOpen(false);
    }
  };

  if (!isAuthenticated) {
    return (
      <button
        type="button"
        className="ag-btn"
        data-variant="primary"
        onClick={() => handle(login)}
        disabled={busy}
      >
        Sign in
      </button>
    );
  }

  const label = active?.account.name ?? active?.account.username ?? 'Signed in';
  const initial = (active?.account.name ?? 'U').charAt(0).toUpperCase();

  return (
    <div style={{ position: 'relative' }}>
      <button
        type="button"
        className="ag-btn"
        data-variant="ghost"
        onClick={() => setMenuOpen((v) => !v)}
        style={{ display: 'inline-flex', alignItems: 'center', gap: 8 }}
        aria-haspopup="menu"
        aria-expanded={menuOpen}
      >
        <span className="ag-avatar" style={{ width: 22, height: 22, fontSize: 11 }}>
          {initial}
        </span>
        <span style={{ fontSize: 12 }}>{label}</span>
        <Icon.ChevronDown width={11} height={11} />
      </button>
      {menuOpen && (
        <div
          role="menu"
          style={{
            position: 'absolute',
            top: 'calc(100% + 4px)',
            right: 0,
            minWidth: 180,
            background: 'var(--ag-surface)',
            border: '1px solid var(--ag-border)',
            borderRadius: 8,
            padding: 4,
            boxShadow: '0 8px 24px rgba(15, 15, 15, 0.12)',
            zIndex: 30,
          }}
        >
          <button
            type="button"
            role="menuitem"
            onClick={() => handle(logout)}
            disabled={busy}
            style={{
              display: 'block',
              width: '100%',
              padding: '8px 12px',
              background: 'transparent',
              border: 'none',
              borderRadius: 6,
              textAlign: 'left',
              cursor: 'pointer',
              fontSize: 13,
              color: 'var(--ag-text)',
            }}
            onMouseEnter={(e) => (e.currentTarget.style.background = 'var(--ag-surface-hover)')}
            onMouseLeave={(e) => (e.currentTarget.style.background = 'transparent')}
          >
            Sign out
          </button>
        </div>
      )}
    </div>
  );
}
