import { useEffect, useRef, useState } from 'react';
import type { CSSProperties } from 'react';
import type { Meeting } from '@ds/lib/seed-data';
import { Icon } from '@ds/lib/icons';

type Size = 'sm' | 'md' | 'lg';

type Props = {
  meetings: Meeting[];
  selectedId: string | null;
  onSelect: (id: string) => void;
  placeholder?: string;
  size?: Size;
};

const TRIGGER_PAD: Record<Size, string> = {
  sm: '4px 8px',
  md: '8px 12px',
  lg: '12px 16px',
};

const TRIGGER_FONT: Record<Size, number> = {
  sm: 12,
  md: 13,
  lg: 14,
};

export function MeetingDropdown({
  meetings,
  selectedId,
  onSelect,
  placeholder = 'Select a meeting',
  size = 'md',
}: Props) {
  const [open, setOpen] = useState(false);
  const rootRef = useRef<HTMLDivElement>(null);
  const selected = meetings.find((m) => m.id === selectedId) ?? null;

  // Click-outside + Escape close. Listening only while open keeps the cost
  // off the global event bus when the menu is dismissed.
  useEffect(() => {
    if (!open) return;
    const onDocDown = (e: MouseEvent) => {
      if (!rootRef.current?.contains(e.target as Node)) setOpen(false);
    };
    const onKey = (e: KeyboardEvent) => {
      if (e.key === 'Escape') setOpen(false);
    };
    document.addEventListener('mousedown', onDocDown);
    document.addEventListener('keydown', onKey);
    return () => {
      document.removeEventListener('mousedown', onDocDown);
      document.removeEventListener('keydown', onKey);
    };
  }, [open]);

  const handlePick = (id: string) => {
    onSelect(id);
    setOpen(false);
  };

  const triggerStyle: CSSProperties = {
    display: 'inline-flex',
    alignItems: 'center',
    gap: 8,
    padding: TRIGGER_PAD[size],
    fontSize: TRIGGER_FONT[size],
    fontWeight: 500,
    color: 'var(--ag-text)',
    background: 'var(--ag-surface)',
    border: '1px solid var(--ag-border)',
    borderRadius: 8,
    cursor: 'pointer',
    minWidth: 220,
    textAlign: 'left',
  };

  return (
    <div ref={rootRef} style={{ position: 'relative', display: 'inline-block' }}>
      <button
        type="button"
        aria-haspopup="listbox"
        aria-expanded={open}
        onClick={() => setOpen((v) => !v)}
        style={triggerStyle}
      >
        <Icon.Calendar width={13} height={13} style={{ color: 'var(--ag-text-muted)' }} />
        <span style={{ flex: 1, overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap' }}>
          {selected ? selected.title : placeholder}
        </span>
        {selected && (
          <span style={{ fontSize: 11, color: 'var(--ag-text-muted)' }}>{selected.detail}</span>
        )}
        <Icon.ChevronDown
          width={12}
          height={12}
          style={{
            color: 'var(--ag-text-muted)',
            transform: open ? 'rotate(180deg)' : 'none',
            transition: 'transform 0.15s',
          }}
        />
      </button>

      {open && (
        <div
          role="listbox"
          style={{
            position: 'absolute',
            top: 'calc(100% + 4px)',
            left: 0,
            minWidth: 320,
            maxHeight: 360,
            overflowY: 'auto',
            background: 'var(--ag-surface)',
            border: '1px solid var(--ag-border)',
            borderRadius: 10,
            boxShadow: '0 8px 24px rgba(15, 15, 15, 0.12)',
            padding: 4,
            zIndex: 30,
          }}
        >
          {meetings.map((m) => {
            const active = m.id === selectedId;
            return (
              <button
                key={m.id}
                type="button"
                role="option"
                aria-selected={active}
                onClick={() => handlePick(m.id)}
                style={{
                  display: 'flex',
                  alignItems: 'center',
                  gap: 10,
                  width: '100%',
                  padding: '10px 12px',
                  background: active ? 'var(--ag-accent-soft)' : 'transparent',
                  border: 'none',
                  borderRadius: 6,
                  textAlign: 'left',
                  cursor: 'pointer',
                  color: 'var(--ag-text)',
                }}
                onMouseEnter={(e) => {
                  if (!active) e.currentTarget.style.background = 'var(--ag-surface-hover)';
                }}
                onMouseLeave={(e) => {
                  if (!active) e.currentTarget.style.background = 'transparent';
                }}
              >
                <Icon.Calendar
                  width={14}
                  height={14}
                  style={{ color: active ? 'var(--ag-accent-text)' : 'var(--ag-text-muted)' }}
                />
                <div style={{ flex: 1, minWidth: 0 }}>
                  <div style={{ fontSize: 13, fontWeight: 500 }}>{m.title}</div>
                  <div style={{ fontSize: 11.5, color: 'var(--ag-text-muted)' }}>{m.detail}</div>
                </div>
                <span className="ag-tag">{m.candidates} candidates</span>
                {active && (
                  <Icon.Check
                    width={12}
                    height={12}
                    style={{ color: 'var(--ag-accent-text)' }}
                  />
                )}
              </button>
            );
          })}
        </div>
      )}
    </div>
  );
}
