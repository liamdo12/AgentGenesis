import { Demo, Pair, PairSide, Section, SubSec } from '../components/ds-primitives';
import { Icon } from '../lib/icons';

const FilterChips = () => (
  <>
    <button type="button" className="ag-chip" data-active="">
      All <span className="ag-chip-count">5</span>
    </button>
    <button type="button" className="ag-chip">
      Pending <span className="ag-chip-count">4</span>
    </button>
    <button type="button" className="ag-chip">
      Approved <span className="ag-chip-count">1</span>
    </button>
    <button type="button" className="ag-chip">
      High priority <span className="ag-chip-count">2</span>
    </button>
  </>
);

export function ChipsSection() {
  return (
    <Section id="chips-tags" title="Chips, tags, pills">
      <SubSec
        title="Filter chip"
        code=".ag-chip[data-active]"
        desc="Toggle filter. Active is an elevated surface. Counts use the mono tabular-nums."
      >
        <Pair>
          <PairSide theme="light"><FilterChips /></PairSide>
          <PairSide theme="dark"><FilterChips /></PairSide>
        </Pair>
      </SubSec>

      <SubSec
        title="Tag"
        code=".ag-tag[data-tag]"
        desc="Source-of-truth color per tag. Never invent ad-hoc tags at the call site."
      >
        <Demo label=".ag-tag">
          <span className="ag-tag" data-tag="Auth">Auth</span>
          <span className="ag-tag" data-tag="Meetings">Meetings</span>
          <span className="ag-tag" data-tag="DevOps">DevOps</span>
          <span className="ag-tag">Default</span>
          <span
            className="ag-tag"
            style={{ background: 'var(--ag-success-soft)', color: 'var(--ag-success)' }}
          >
            <Icon.Check width={10} height={10} /> Approved
          </span>
        </Demo>
      </SubSec>

      <SubSec
        title="Priority pill"
        code=".ag-priority[data-level]"
        desc="Three levels. Uppercase + tracking 0.04em. Never use elsewhere — reserved for story priority."
      >
        <Demo label=".ag-priority">
          <span className="ag-priority" data-level="high">high</span>
          <span className="ag-priority" data-level="med">med</span>
          <span className="ag-priority" data-level="low">low</span>
        </Demo>
      </SubSec>

      <SubSec
        title="Status pill"
        code=".ag-status-pill"
        desc="Live connection status. Pulses on the success token. Singleton per surface."
      >
        <Pair>
          <PairSide theme="light">
            <span className="ag-status-pill">Claude · Connected</span>
          </PairSide>
          <PairSide theme="dark">
            <span className="ag-status-pill">Claude · Connected</span>
          </PairSide>
        </Pair>
      </SubSec>

      <SubSec title="KBD" code=".ag-kbd" desc="Inline keyboard hint. Mono, surface-2 fill, hairline border.">
        <Demo label=".ag-kbd">
          <span className="ag-kbd">⌘K</span>
          <span className="ag-kbd">⌘F</span>
          <span className="ag-kbd">↵</span>
          <span className="ag-kbd">Esc</span>
        </Demo>
      </SubSec>

      <SubSec
        title="Avatar"
        code=".ag-avatar"
        desc="26px circle, gradient fill, initials. Avoid photos — initials read better at this size."
      >
        <Demo label=".ag-avatar">
          <span className="ag-avatar">RP</span>
          <span className="ag-avatar" style={{ background: 'linear-gradient(135deg, #5b53e8, #8b5cf6)' }}>AM</span>
          <span className="ag-avatar" style={{ background: 'linear-gradient(135deg, #0e9f6e, #06b6d4)' }}>JK</span>
        </Demo>
      </SubSec>
    </Section>
  );
}
