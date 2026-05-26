import { Pair, PairSide, Section, SubSec } from '../components/ds-primitives';
import { Icon } from '../lib/icons';

const EmptyContent = () => (
  <div style={{ width: '100%' }}>
    <div className="ag-empty" style={{ padding: 32 }}>
      <div className="ag-empty-icon">
        <Icon.Inbox width={20} height={20} />
      </div>
      <div className="ag-empty-title">No stories yet</div>
      <div className="ag-empty-sub">
        Connect a meeting recording or paste a transcript to get started.
      </div>
      <button type="button" className="ag-btn" data-variant="primary">
        <Icon.Plus width={12} height={12} /> Select a meeting
      </button>
    </div>
  </div>
);

export function EmptyStateSection() {
  return (
    <Section id="empty-state" title="Empty state">
      <SubSec
        title=".ag-empty"
        desc="Centered icon plate · 16px title · muted 13px subhead · primary CTA. Reserve for terminal empty surfaces; not for filter resets."
      >
        <Pair>
          <PairSide theme="light"><EmptyContent /></PairSide>
          <PairSide theme="dark"><EmptyContent /></PairSide>
        </Pair>
      </SubSec>
    </Section>
  );
}
