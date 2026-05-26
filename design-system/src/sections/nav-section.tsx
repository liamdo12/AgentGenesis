import { Demo, Pair, PairSide, Section, SubSec } from '../components/ds-primitives';
import { AgTopBar } from '../components/ag-topbar';
import { Icon } from '../lib/icons';

export function NavSection() {
  return (
    <Section id="nav" title="Top bar & tabs">
      <SubSec
        title="Top bar"
        code=".ag-topbar"
        desc="Brand left · segmented tab nav center · search + status + avatar right. 52px tall, hairline bottom border."
      >
        <Pair>
          <PairSide theme="light">
            <div style={{ width: '100%', margin: -28 }}>
              <AgTopBar activeTab="Stories" />
            </div>
          </PairSide>
          <PairSide theme="dark">
            <div style={{ width: '100%', margin: -28 }}>
              <AgTopBar activeTab="Stories" />
            </div>
          </PairSide>
        </Pair>
      </SubSec>

      <SubSec
        title="Segmented tabs"
        code=".ag-tabs > .ag-tab[data-active]"
        desc="3-up tab control. Thumb is an elevated white surface."
      >
        <Demo label=".ag-tabs">
          <div className="ag-tabs">
            <button type="button" className="ag-tab">
              <Icon.Calendar width={12} height={12} /> Meetings
            </button>
            <button type="button" className="ag-tab" data-active="">
              <Icon.List width={12} height={12} /> Stories
            </button>
            <button type="button" className="ag-tab">
              <Icon.Dash width={12} height={12} /> Dashboard
            </button>
          </div>
        </Demo>
      </SubSec>
    </Section>
  );
}
