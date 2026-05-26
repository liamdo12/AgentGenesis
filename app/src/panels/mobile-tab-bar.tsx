import { Icon } from '@ds/lib/icons';

export type MobileTab = 'stories' | 'assistant';

type Props = {
  active: MobileTab;
  onPick: (tab: MobileTab) => void;
  pendingCount: number;
};

export function MobileTabBar({ active, onPick, pendingCount }: Props) {
  return (
    <div className="ag-mobile-tabs mobile-tab-bar">
      <TabButton id="stories"   icon="List"    label="Stories"   active={active} onPick={onPick} badge={pendingCount} />
      <TabButton id="assistant" icon="Sparkle" label="Assistant" active={active} onPick={onPick} badge={4} />
    </div>
  );
}

function TabButton({
  id,
  icon,
  label,
  active,
  onPick,
  badge,
}: {
  id: MobileTab;
  icon: 'List' | 'Sparkle';
  label: string;
  active: MobileTab;
  onPick: (id: MobileTab) => void;
  badge: number;
}) {
  const isActive = id === active;
  const Ic = Icon[icon];
  return (
    <button
      type="button"
      className="ag-mobile-tab"
      data-active={isActive ? '' : undefined}
      onClick={() => onPick(id)}
    >
      <Ic width={13} height={13} /> {label}
      <span
        className="ag-mobile-tab-badge"
        style={{
          background: isActive ? 'var(--ag-accent)' : 'var(--ag-surface-hover)',
          color: isActive ? 'white' : 'var(--ag-text-muted)',
        }}
      >
        {badge}
      </span>
    </button>
  );
}
