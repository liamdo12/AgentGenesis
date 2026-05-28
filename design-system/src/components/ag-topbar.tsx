import type { ReactNode } from 'react';
import { Icon, type IconName } from '../lib/icons';

export type TabId = 'Meetings' | 'Stories' | 'Dashboard';

type TopBarProps = {
  activeTab?: TabId;
  onTab?: (id: TabId) => void;
  dark?: boolean;
  onToggleDark?: () => void;
  // Slot for app-supplied right-side content (e.g. auth button). When provided,
  // it replaces the default Search/theme/status/avatar block. Per red-team
  // Finding 11 of the SSO plan.
  right?: ReactNode;
};

const TABS: { id: TabId; icon: IconName }[] = [
  { id: 'Meetings', icon: 'Calendar' },
  { id: 'Stories', icon: 'List' },
  { id: 'Dashboard', icon: 'Dash' },
];

export function AgTopBar({
  activeTab = 'Stories',
  onTab,
  dark,
  onToggleDark,
  right,
}: TopBarProps) {
  return (
    <div className="ag-topbar">
      <div className="ag-brand">
        <span className="ag-brand-mark">AG</span>
        <span>Agent Genesis</span>
      </div>
      <div className="ag-tabs" role="tablist">
        {TABS.map((t) => {
          const Ic = Icon[t.icon];
          const isActive = activeTab === t.id;
          return (
            <button
              key={t.id}
              type="button"
              className="ag-tab"
              role="tab"
              aria-selected={isActive}
              {...(isActive ? { 'data-active': '' } : {})}
              onClick={() => onTab?.(t.id)}
            >
              <Ic width={12} height={12} /> {t.id}
            </button>
          );
        })}
      </div>
      <div className="ag-topbar-right">
        {right ?? (
          <>
            <button
              type="button"
              className="ag-btn"
              data-variant="ghost"
              style={{ height: 28, padding: '0 8px', gap: 8 }}
              title="Search"
            >
              <Icon.Search width={12} height={12} />
              <span style={{ color: 'var(--ag-text-muted)' }}>Search</span>
              <span className="ag-kbd">⌘K</span>
            </button>
            {onToggleDark && (
              <button type="button" className="ag-iconbtn" onClick={onToggleDark} title="Toggle theme">
                {dark ? <Icon.Sun /> : <Icon.Moon />}
              </button>
            )}
            <span className="ag-status-pill">Claude · Connected</span>
            <span className="ag-avatar">RP</span>
          </>
        )}
      </div>
    </div>
  );
}
