import { Pair, PairSide, Section, SubSec } from '../components/ds-primitives';
import { Icon } from '../lib/icons';

const StatPair = () => (
  <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 12, width: '100%' }}>
    <div className="ag-stat">
      <div className="ag-stat-label">Approved</div>
      <div className="ag-stat-value">98</div>
      <div className="ag-stat-delta">
        <Icon.ArrowUp width={10} height={10} /> +22 this week
      </div>
    </div>
    <div className="ag-stat">
      <div className="ag-stat-label">Avg approval time</div>
      <div className="ag-stat-value">4m 12s</div>
      <div className="ag-stat-delta">
        <Icon.ArrowUp width={10} height={10} /> −24% vs last
      </div>
    </div>
  </div>
);

const ROADMAP_ROWS = [
  { c: 'var(--ag-success)', label: 'Meeting ingestion',     meta: '8 / 8 stories',   pct: 100 },
  { c: 'var(--ag-accent)',  label: 'AI story extraction',   meta: '12 / 14 stories', pct: 86 },
  { c: '#f59e0b',           label: 'Approval & priority',   meta: '6 / 10 stories',  pct: 60 },
];

const RoadmapRows = () => (
  <div className="ag-roadmap" style={{ width: '100%' }}>
    {ROADMAP_ROWS.map((r, i) => (
      <div key={i} className="ag-roadmap-row">
        <span className="ag-roadmap-dot" style={{ background: r.c }} />
        <div>
          <div style={{ fontSize: 13, fontWeight: 500 }}>{r.label}</div>
          <div style={{ fontSize: 11.5, color: 'var(--ag-text-muted)' }}>{r.meta}</div>
        </div>
        <div className="ag-roadmap-bar">
          <div style={{ width: `${r.pct}%`, background: r.c }} />
        </div>
        <div className="ag-roadmap-pct">{r.pct}%</div>
      </div>
    ))}
  </div>
);

export function StatsRoadmapSection() {
  return (
    <Section id="stats-roadmap" title="Stats & roadmap">
      <SubSec
        title="Stat card"
        code=".ag-stat"
        desc="Mono label / 26 tabular value / success delta. Sit in a 4-column grid on the dashboard."
      >
        <Pair>
          <PairSide theme="light"><StatPair /></PairSide>
          <PairSide theme="dark"><StatPair /></PairSide>
        </Pair>
      </SubSec>

      <SubSec
        title="Roadmap row"
        code=".ag-roadmap-row"
        desc="Status dot · label/meta · progress bar · percent. The dot, bar color, and percent share a single hue per row."
      >
        <Pair>
          <PairSide theme="light"><RoadmapRows /></PairSide>
          <PairSide theme="dark"><RoadmapRows /></PairSide>
        </Pair>
      </SubSec>
    </Section>
  );
}
