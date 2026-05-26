import { Icon } from '@ds/lib/icons';

const STATS = [
  { label: 'Stories extracted',  value: '142',    delta: '+38 this week' },
  { label: 'Approved',           value: '98',     delta: '+22 this week' },
  { label: 'Pushed to DevOps',   value: '76',     delta: '+19 this week' },
  { label: 'Avg approval time',  value: '4m 12s', delta: '−24% vs last' },
];

const ACTIVITY = [
  [40, 28, 18], [55, 40, 22], [30, 18, 10], [70, 55, 38],
  [60, 48, 30], [85, 70, 52], [45, 35, 22], [62, 50, 38],
  [78, 65, 48], [92, 80, 65], [50, 38, 24], [68, 55, 42],
  [88, 72, 55], [110, 92, 78],
];

const ROADMAP = [
  { color: 'var(--ag-success)',      label: 'Meeting transcript ingestion',  meta: '8 / 8 stories',   pct: 100 },
  { color: 'var(--ag-accent)',       label: 'AI story extraction (Claude)',  meta: '12 / 14 stories', pct: 86 },
  { color: '#f59e0b',                label: 'Approval & priority workflow',  meta: '6 / 10 stories',  pct: 60 },
  { color: '#0078d4',                label: 'Azure DevOps bidirectional sync', meta: '3 / 8 stories', pct: 38 },
  { color: 'var(--ag-text-faint)',   label: 'Multi-tenant + SSO hardening',  meta: '0 / 6 stories',   pct: 0 },
];

export function DashboardPanel() {
  return (
    <div className="ag-main">
      <div className="ag-stories-col" style={{ borderRight: 0 }}>
        <div className="ag-subhead">
          <div>
            <div className="ag-subhead-title">Dashboard</div>
            <div className="ag-subhead-meta">Last 30 days · all meetings</div>
          </div>
          <div className="ag-subhead-actions">
            <button type="button" className="ag-btn">
              <Icon.Calendar width={12} height={12} /> Aug 2025
            </button>
            <button type="button" className="ag-btn">
              <Icon.Sort width={12} height={12} /> Export
            </button>
          </div>
        </div>

        <div className="ag-dash">
          <div className="ag-dash-grid">
            {STATS.map((s) => (
              <div key={s.label} className="ag-stat">
                <div className="ag-stat-label">{s.label}</div>
                <div className="ag-stat-value">{s.value}</div>
                <div className="ag-stat-delta">
                  <Icon.ArrowUp width={10} height={10} /> {s.delta}
                </div>
              </div>
            ))}
          </div>

          <h3 className="ag-section-title">Activity <span>last 14 days</span></h3>
          <div
            style={{
              background: 'var(--ag-surface)',
              border: '1px solid var(--ag-border)',
              borderRadius: 10,
              padding: '18px 18px 12px',
              marginBottom: 24,
            }}
          >
            <div
              style={{
                display: 'flex',
                gap: 16,
                fontSize: 11.5,
                color: 'var(--ag-text-muted)',
                marginBottom: 14,
              }}
            >
              <LegendChip color="var(--ag-accent)" label="Extracted" />
              <LegendChip color="var(--ag-success)" label="Approved" />
              <LegendChip color="#0078d4" label="Pushed" />
            </div>
            <div style={{ display: 'flex', alignItems: 'flex-end', gap: 8, height: 140 }}>
              {ACTIVITY.map((bars, i) => (
                <div
                  key={i}
                  style={{
                    flex: 1,
                    display: 'flex',
                    flexDirection: 'column',
                    alignItems: 'center',
                    gap: 2,
                  }}
                >
                  <div
                    style={{
                      display: 'flex',
                      alignItems: 'flex-end',
                      height: 120,
                      gap: 2,
                      width: '100%',
                    }}
                  >
                    <Bar height={bars[0]} color="var(--ag-accent)" />
                    <Bar height={bars[1]} color="var(--ag-success)" />
                    <Bar height={bars[2]} color="#0078d4" />
                  </div>
                  <span
                    style={{
                      fontSize: 10,
                      color: 'var(--ag-text-faint)',
                      fontVariantNumeric: 'tabular-nums',
                    }}
                  >
                    {i + 9}
                  </span>
                </div>
              ))}
            </div>
          </div>

          <h3 className="ag-section-title">Phase 1 roadmap <span>Q3 2025</span></h3>
          <div className="ag-roadmap">
            {ROADMAP.map((r) => (
              <div key={r.label} className="ag-roadmap-row">
                <span className="ag-roadmap-dot" style={{ background: r.color }} />
                <div>
                  <div style={{ fontSize: 13, fontWeight: 500 }}>{r.label}</div>
                  <div style={{ fontSize: 11.5, color: 'var(--ag-text-muted)' }}>{r.meta}</div>
                </div>
                <div className="ag-roadmap-bar">
                  <div style={{ width: `${r.pct}%`, background: r.color }} />
                </div>
                <div className="ag-roadmap-pct">{r.pct}%</div>
              </div>
            ))}
          </div>
        </div>
      </div>
    </div>
  );
}

function LegendChip({ color, label }: { color: string; label: string }) {
  return (
    <span style={{ display: 'inline-flex', alignItems: 'center', gap: 5 }}>
      <i style={{ width: 8, height: 8, borderRadius: 2, background: color }} /> {label}
    </span>
  );
}

function Bar({ height, color }: { height: number; color: string }) {
  return (
    <div
      style={{
        flex: 1,
        height,
        background: color,
        borderRadius: '2px 2px 0 0',
        opacity: 0.85,
      }}
    />
  );
}
