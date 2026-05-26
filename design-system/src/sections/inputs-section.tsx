import { Demo, Pair, PairSide, Section, SubSec } from '../components/ds-primitives';
import { Icon } from '../lib/icons';

export function InputsSection() {
  return (
    <Section id="inputs" title="Inputs">
      <SubSec
        title="Text & textarea"
        code=".ag-field"
        desc="Mono uppercase label, hairline border, indigo focus ring (3px accent-soft)."
      >
        <Pair>
          <PairSide theme="light">
            <div style={{ display: 'flex', flexDirection: 'column', gap: 12, width: '100%' }}>
              <div className="ag-field">
                <label>Title</label>
                <input defaultValue="Meeting transcript auto-fetch" />
              </div>
              <div className="ag-field">
                <label>Acceptance criteria</label>
                <textarea
                  rows={3}
                  defaultValue={`Given I'm authenticated\nWhen I select a meeting\nThen the transcript loads within 3 seconds`}
                />
              </div>
              <div className="ag-field">
                <label>Priority</label>
                <select defaultValue="high">
                  <option>high</option>
                  <option>med</option>
                  <option>low</option>
                </select>
              </div>
            </div>
          </PairSide>
          <PairSide theme="dark">
            <div style={{ display: 'flex', flexDirection: 'column', gap: 12, width: '100%' }}>
              <div className="ag-field">
                <label>Title</label>
                <input defaultValue="Meeting transcript auto-fetch" />
              </div>
              <div className="ag-field">
                <label>Priority</label>
                <select defaultValue="high">
                  <option>high</option>
                  <option>med</option>
                  <option>low</option>
                </select>
              </div>
            </div>
          </PairSide>
        </Pair>
      </SubSec>

      <SubSec title="Search" code=".ag-search" desc="Icon left, kbd hint right. Same focus ring as fields.">
        <Pair>
          <PairSide theme="light">
            <div className="ag-search" style={{ width: 320 }}>
              <span className="ag-search-icon">
                <Icon.Search />
              </span>
              <input placeholder="Search by title, ID, AC…" />
              <span className="ag-kbd">⌘F</span>
            </div>
          </PairSide>
          <PairSide theme="dark">
            <div className="ag-search" style={{ width: 320 }}>
              <span className="ag-search-icon">
                <Icon.Search />
              </span>
              <input placeholder="Search by title, ID, AC…" />
              <span className="ag-kbd">⌘F</span>
            </div>
          </PairSide>
        </Pair>
      </SubSec>

      <SubSec
        title="Checkbox · selection"
        code=".ag-card-check[data-checked]"
        desc="The story-card selector. 16×16 with the indigo accent when checked."
      >
        <Demo label=".ag-card-check">
          <button type="button" className="ag-card-check" />
          <button type="button" className="ag-card-check" data-checked="">
            <Icon.CheckSmall width={11} height={11} />
          </button>
        </Demo>
      </SubSec>
    </Section>
  );
}
