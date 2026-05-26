import { Demo, Pair, PairSide, Section, SubSec } from '../components/ds-primitives';
import { Icon } from '../lib/icons';

export function ButtonsSection() {
  return (
    <Section id="buttons" title="Buttons">
      <SubSec
        title="Variants"
        code=".ag-btn[data-variant]"
        desc="Three intents. Primary = the one push-forward action per surface. Default = anything else. Ghost = lowest-emphasis tools."
      >
        <Pair>
          <PairSide theme="light">
            <button type="button" className="ag-btn" data-variant="primary">
              <Icon.Plus width={12} height={12} /> New story
            </button>
            <button type="button" className="ag-btn">
              <Icon.Sparkle width={12} height={12} /> Re-extract
            </button>
            <button type="button" className="ag-btn" data-variant="ghost">
              <Icon.Sort width={12} height={12} /> Priority
            </button>
          </PairSide>
          <PairSide theme="dark">
            <button type="button" className="ag-btn" data-variant="primary">
              <Icon.Plus width={12} height={12} /> New story
            </button>
            <button type="button" className="ag-btn">
              <Icon.Sparkle width={12} height={12} /> Re-extract
            </button>
            <button type="button" className="ag-btn" data-variant="ghost">
              <Icon.Sort width={12} height={12} /> Priority
            </button>
          </PairSide>
        </Pair>
      </SubSec>

      <SubSec
        title="Sizes"
        code=".ag-btn[data-size]"
        desc="Default 28px, large 32px. Smaller sizes live in card actions and aren't part of the button family."
      >
        <Demo label="default">
          <button type="button" className="ag-btn">Default · 28</button>
          <button type="button" className="ag-btn" data-variant="primary">Primary · 28</button>
          <button type="button" className="ag-btn" data-size="lg">Large · 32</button>
          <button type="button" className="ag-btn" data-variant="primary" data-size="lg">Primary · 32</button>
        </Demo>
      </SubSec>

      <SubSec title="Icon button" code=".ag-iconbtn" desc="26×26 square hit target. Toggle state via data-on.">
        <Demo label=".ag-iconbtn">
          <button type="button" className="ag-iconbtn"><Icon.More /></button>
          <button type="button" className="ag-iconbtn" data-on=""><Icon.List /></button>
          <button type="button" className="ag-iconbtn"><Icon.Dash /></button>
          <button type="button" className="ag-iconbtn"><Icon.Edit /></button>
          <button type="button" className="ag-iconbtn"><Icon.Trash /></button>
        </Demo>
      </SubSec>

      <SubSec title="Spec">
        <div className="ds-specs">
          <div>
            <b>height</b>
            <span>Default 28 · large 32. Avoid &lt;26px hit targets.</span>
            <em>28 / 32</em>
          </div>
          <div>
            <b>padding</b>
            <span>11px horizontal default; 13px large.</span>
            <em>0 11 / 0 13</em>
          </div>
          <div>
            <b>radius</b>
            <span>6px on all variants.</span>
            <em>6</em>
          </div>
          <div>
            <b>icon size</b>
            <span>12px inside buttons; 14px in icon-only buttons.</span>
            <em>12 / 14</em>
          </div>
          <div>
            <b>gap</b>
            <span>6px between icon and label.</span>
            <em>6</em>
          </div>
        </div>
      </SubSec>
    </Section>
  );
}
