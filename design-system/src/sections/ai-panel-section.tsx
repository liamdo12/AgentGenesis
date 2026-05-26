import { Pair, PairSide, Section, SubSec } from '../components/ds-primitives';
import {
  AgAIHeader,
  AgComposer,
  AgContextStrip,
  AgMessage,
  AgQuickBar,
} from '../components/ag-ai-panel';

const wrap = {
  width: '100%',
  background: 'var(--ag-surface)',
  borderRadius: 8,
  border: '1px solid var(--ag-border)',
  overflow: 'hidden' as const,
};

export function AIPanelSection() {
  return (
    <Section id="ai-panel" title="AI assistant">
      <SubSec
        title="Panel header"
        code=".ag-ai-head"
        desc="Gradient mark · status sub-line with success pulse · clear + settings."
      >
        <Pair>
          <PairSide theme="light">
            <div style={wrap}>
              <AgAIHeader />
              <AgContextStrip count={3} />
              <div style={{ height: 12 }} />
            </div>
          </PairSide>
          <PairSide theme="dark">
            <div style={wrap}>
              <AgAIHeader />
              <AgContextStrip count={3} />
              <div style={{ height: 12 }} />
            </div>
          </PairSide>
        </Pair>
      </SubSec>

      <SubSec
        title="Message bubble"
        code=".ag-msg"
        desc="Avatar + body. AI uses the gradient sparkle mark; users get a flat surface badge. Cards may be attached for structured replies (extraction results, etc.)"
      >
        <Pair>
          <PairSide theme="light">
            <div style={{ display: 'flex', flexDirection: 'column', gap: 12, width: '100%' }}>
              <AgMessage
                from="ai"
                body={
                  <p>
                    Hi! I'm your Agent Genesis assistant. Extract stories from a meeting, then ask me to
                    approve, prioritise, or split them.
                  </p>
                }
                time="10:42"
              />
              <AgMessage
                from="ai"
                body={
                  <p>
                    Found <strong>3 user stories</strong> in <em>Sprint Planning · Aug 22</em>.
                  </p>
                }
                card={[
                  { txt: 'AG-024 · User authentication with SSO', ok: true },
                  { txt: 'AG-025 · Meeting transcript auto-fetch', ok: true },
                  { txt: 'AG-026 · Bulk story export to DevOps', ok: true },
                ]}
                time="10:42"
              />
              <AgMessage from="user" body={<p>approve all</p>} time="10:43" />
              <AgMessage from="ai" typing />
            </div>
          </PairSide>
          <PairSide theme="dark">
            <div style={{ display: 'flex', flexDirection: 'column', gap: 12, width: '100%' }}>
              <AgMessage
                from="ai"
                body={
                  <p>
                    Found <strong>3 user stories</strong> from that meeting.
                  </p>
                }
                card={[
                  { txt: 'AG-024 · User authentication with SSO', ok: true },
                  { txt: 'AG-025 · Meeting transcript auto-fetch', ok: true },
                ]}
                time="10:42"
              />
              <AgMessage from="user" body={<p>approve all</p>} time="10:43" />
              <AgMessage from="ai" typing />
            </div>
          </PairSide>
        </Pair>
      </SubSec>

      <SubSec
        title="Suggested actions"
        code=".ag-quickbar"
        desc="Contextual chip rail above the composer. 2–6 items, ordered by likely action. Always include the destructive shipping action (push) and the highest-value AI action."
      >
        <Pair>
          <PairSide theme="light">
            <div style={{ width: '100%', background: 'var(--ag-surface)', borderRadius: 8, border: '1px solid var(--ag-border)' }}>
              <AgQuickBar />
            </div>
          </PairSide>
          <PairSide theme="dark">
            <div style={{ width: '100%', background: 'var(--ag-surface)', borderRadius: 8, border: '1px solid var(--ag-border)' }}>
              <AgQuickBar />
            </div>
          </PairSide>
        </Pair>
      </SubSec>

      <SubSec
        title="Composer"
        code=".ag-composer"
        desc="Multi-line textarea that auto-grows to 120px max. Send is disabled until non-empty."
      >
        <Pair>
          <PairSide theme="light">
            <div style={{ width: '100%', background: 'var(--ag-surface)', borderRadius: 8, border: '1px solid var(--ag-border)' }}>
              <AgComposer value="Split AG-026 into UI and API tickets" onChange={() => {}} />
            </div>
          </PairSide>
          <PairSide theme="dark">
            <div style={{ width: '100%', background: 'var(--ag-surface)', borderRadius: 8, border: '1px solid var(--ag-border)' }}>
              <AgComposer value="" onChange={() => {}} />
            </div>
          </PairSide>
        </Pair>
      </SubSec>
    </Section>
  );
}
