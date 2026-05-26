import { Pair, PairSide, Section, SubSec } from '../components/ds-primitives';
import { Icon } from '../lib/icons';

function ModalDemo() {
  return (
    <div
      style={{
        position: 'absolute',
        inset: 0,
        background: 'rgba(15,15,15,0.4)',
        borderRadius: 8,
        display: 'flex',
        alignItems: 'center',
        justifyContent: 'center',
        padding: 16,
      }}
    >
      <div
        style={{
          background: 'var(--ag-surface)',
          border: '1px solid var(--ag-border)',
          borderRadius: 10,
          boxShadow: 'var(--ag-shadow-lg)',
          width: '100%',
          maxWidth: 360,
          overflow: 'hidden',
        }}
      >
        <div className="ag-modal-head" style={{ padding: '12px 14px' }}>
          <span className="ag-card-id" style={{ marginTop: 0 }}>AG-025</span>
          <span className="ag-priority" data-level="high">high</span>
          <div className="ag-modal-title" style={{ fontSize: 14 }}>Edit story</div>
          <button type="button" className="ag-iconbtn" style={{ marginLeft: 'auto' }}>
            <Icon.X />
          </button>
        </div>
        <div className="ag-modal-body" style={{ padding: '14px' }}>
          <div className="ag-field">
            <label>Title</label>
            <input defaultValue="Meeting transcript auto-fetch" />
          </div>
        </div>
        <div className="ag-modal-foot" style={{ padding: '10px 14px' }}>
          <div style={{ marginLeft: 'auto', display: 'flex', gap: 6 }}>
            <button type="button" className="ag-btn">Cancel</button>
            <button type="button" className="ag-btn" data-variant="primary">Save</button>
          </div>
        </div>
      </div>
    </div>
  );
}

export function ModalSection() {
  const stageStyle = {
    width: '100%',
    position: 'relative' as const,
    height: 340,
    background: 'var(--ag-bg)',
    borderRadius: 8,
    border: '1px solid var(--ag-border)',
  };
  return (
    <Section id="modal" title="Modal">
      <SubSec
        title="Anatomy"
        code=".ag-modal"
        desc="Backdrop @ 40% black + 2px blur. Card is surface, hairline borders, large shadow. Head = title/meta + close; body = scrollable fields; foot = sticky CTA row on a sunken surface."
      >
        <Pair>
          <PairSide theme="light">
            <div style={stageStyle}><ModalDemo /></div>
          </PairSide>
          <PairSide theme="dark">
            <div style={stageStyle}><ModalDemo /></div>
          </PairSide>
        </Pair>
      </SubSec>
    </Section>
  );
}
