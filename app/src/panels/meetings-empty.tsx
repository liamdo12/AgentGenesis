import { Icon } from '@ds/lib/icons';

const RECENT_MEETINGS = [
  { title: 'Sprint Planning',            detail: 'Aug 22 · 42 min', candidates: 3 },
  { title: 'Customer Discovery — Acme',  detail: 'Aug 21 · 28 min', candidates: 5 },
  { title: 'Retro · Sprint 14',          detail: 'Aug 20 · 35 min', candidates: 2 },
];

export function MeetingsEmpty() {
  return (
    <div className="ag-stories-col">
      <div className="ag-subhead">
        <div>
          <div className="ag-subhead-title">
            Stories <span className="ag-subhead-count">0</span>
          </div>
          <div className="ag-subhead-meta">No stories extracted yet</div>
        </div>
        <div className="ag-subhead-actions">
          <button type="button" className="ag-btn" data-variant="primary">
            <Icon.Plus width={12} height={12} /> New story
          </button>
        </div>
      </div>

      <div className="ag-empty" style={{ paddingTop: 60 }}>
        <div className="ag-empty-icon" style={{ width: 64, height: 64, borderRadius: 16 }}>
          <Icon.Calendar width={24} height={24} />
        </div>
        <div className="ag-empty-title">No stories yet</div>
        <div className="ag-empty-sub">
          Connect a meeting recording, paste a transcript, or invite Genesis Bot to your next call.
          Stories will appear here.
        </div>
        <div style={{ display: 'flex', gap: 8 }}>
          <button type="button" className="ag-btn" data-variant="primary" data-size="lg">
            <Icon.Calendar width={13} height={13} /> Select a meeting
          </button>
          <button type="button" className="ag-btn" data-size="lg">
            <Icon.Plus width={13} height={13} /> Paste transcript
          </button>
        </div>

        <div style={{ marginTop: 32, width: '100%', maxWidth: 480 }}>
          <div
            style={{
              fontSize: 11,
              fontWeight: 600,
              color: 'var(--ag-text-muted)',
              textTransform: 'uppercase',
              letterSpacing: '0.05em',
              fontFamily: 'var(--ag-mono)',
              marginBottom: 10,
              textAlign: 'left',
            }}
          >
            Recent meetings
          </div>
          <div style={{ display: 'flex', flexDirection: 'column', gap: 6 }}>
            {RECENT_MEETINGS.map((m) => (
              <button
                key={m.title}
                type="button"
                style={{
                  display: 'flex',
                  alignItems: 'center',
                  gap: 10,
                  padding: '10px 12px',
                  background: 'var(--ag-surface)',
                  border: '1px solid var(--ag-border)',
                  borderRadius: 8,
                  textAlign: 'left',
                  cursor: 'pointer',
                }}
              >
                <Icon.Calendar width={14} height={14} style={{ color: 'var(--ag-text-muted)' }} />
                <div style={{ flex: 1 }}>
                  <div style={{ fontSize: 13, fontWeight: 500 }}>{m.title}</div>
                  <div style={{ fontSize: 11.5, color: 'var(--ag-text-muted)' }}>{m.detail}</div>
                </div>
                <span className="ag-tag">{m.candidates} candidates</span>
                <Icon.ChevronRight width={12} height={12} style={{ color: 'var(--ag-text-muted)' }} />
              </button>
            ))}
          </div>
        </div>
      </div>
    </div>
  );
}
