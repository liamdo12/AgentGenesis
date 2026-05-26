import { Section, SubSec } from '../components/ds-primitives';
import { AgBulkBar } from '../components/ag-bulk-bar';

type StageProps = { theme: 'light' | 'dark' };

const Stage = ({ theme }: StageProps) => (
  <div
    className="ag-app"
    data-theme={theme}
    data-density="compact"
    style={{
      position: 'relative',
      height: 120,
      width: '100%',
      background: 'var(--ag-bg)',
      borderRadius: 8,
      border: '1px solid var(--ag-border)',
      overflow: 'hidden',
    }}
  >
    <AgBulkBar count={3} />
  </div>
);

export function BulkBarSection() {
  return (
    <Section id="bulk-bar" title="Bulk toolbar">
      <SubSec
        title="Floating selection bar"
        code=".ag-bulkbar"
        desc="Slides up from the bottom when at least one card is selected. Inverts on theme — dark text on light surface in light mode, the reverse in dark. The primary action is push-to-DevOps because that's the shipping moment."
      >
        <div style={{ display: 'flex', flexDirection: 'column', gap: 12 }}>
          <Stage theme="light" />
          <Stage theme="dark" />
        </div>
      </SubSec>
    </Section>
  );
}
