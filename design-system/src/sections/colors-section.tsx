import { Section, SubSec, Swatch } from '../components/ds-primitives';

const SEMANTIC = [
  { name: 'Background',         token: '--ag-bg',             hexL: '#fbfbfa',                  hexD: '#0a0a0b' },
  { name: 'Surface',            token: '--ag-surface',        hexL: '#ffffff',                  hexD: '#121214' },
  { name: 'Surface · 2',        token: '--ag-surface-2',      hexL: '#f7f7f6',                  hexD: '#18181b' },
  { name: 'Border',             token: '--ag-border',         hexL: 'rgba(15,15,15,0.08)',      hexD: 'rgba(255,255,255,0.08)' },
  { name: 'Text · primary',     token: '--ag-text',           hexL: '#18181b',                  hexD: '#f4f4f5' },
  { name: 'Text · secondary',   token: '--ag-text-secondary', hexL: '#52525b',                  hexD: '#a1a1aa' },
  { name: 'Text · muted',       token: '--ag-text-muted',     hexL: '#8a8a93',                  hexD: '#71717a' },
  { name: 'Text · faint',       token: '--ag-text-faint',     hexL: '#b4b4bb',                  hexD: '#52525b' },
];

const BRAND = [
  { name: 'Accent',         token: '--ag-accent',      hex: '#5b53e8' },
  { name: 'Accent · soft',  token: '--ag-accent-soft', hex: '#eeedfd' },
  { name: 'Accent · text',  token: '--ag-accent-text', hex: '#4940d3' },
  { name: 'Claude · AI',    token: '--ag-ai',          hex: '#7c5cff' },
  { name: 'Success',        token: '--ag-success',     hex: '#0e9f6e' },
  { name: 'Success · soft', token: '--ag-success-soft', hex: '#e7f7f0' },
];

const PRIORITY = [
  { name: 'High',        token: '--ag-prio-high',    hex: '#c53030' },
  { name: 'High · bg',   token: '--ag-prio-high-bg', hex: '#fdecec' },
  { name: 'Medium',      token: '--ag-prio-med',     hex: '#b15c00' },
  { name: 'Medium · bg', token: '--ag-prio-med-bg',  hex: '#fdf2e0' },
  { name: 'Low',         token: '--ag-prio-low',     hex: '#166534' },
  { name: 'Low · bg',    token: '--ag-prio-low-bg',  hex: '#e5f4ea' },
];

const TAGS = [
  { name: 'Auth',     hex: '#4338ca', bg: '#ecebfb' },
  { name: 'Meetings', hex: '#6d28d9', bg: '#f1ebfd' },
  { name: 'DevOps',   hex: '#0e7490', bg: '#e3f5f8' },
  { name: 'Default',  hex: '#525252', bg: '#f1f1f0' },
];

export function ColorsSection() {
  return (
    <Section id="colors" title="Color">
      <SubSec
        title="Semantic scale"
        desc="Every surface, text, and border in the app routes through these. Each ships a light and a dark value — apply via data-theme on .ag-app."
      >
        <div className="ds-palette" style={{ marginBottom: 12 }}>
          {SEMANTIC.map((s) => (
            <Swatch key={s.token + 'l'} name={s.name} token={s.token} hex={s.hexL} color={s.hexL} />
          ))}
        </div>
        <div className="ds-palette">
          {SEMANTIC.map((s) => (
            <Swatch key={s.token + 'd'} name={s.name} token={s.token} hex={s.hexD} color={s.hexD} dark />
          ))}
        </div>
      </SubSec>

      <SubSec
        title="Brand & status"
        desc="A single indigo accent carries every interactive moment. Claude's purple is reserved for AI-attributed surfaces only."
      >
        <div className="ds-palette">
          {BRAND.map((s) => (
            <Swatch key={s.token} name={s.name} token={s.token} hex={s.hex} color={s.hex} />
          ))}
        </div>
      </SubSec>

      <SubSec title="Priority" desc="High / medium / low. Foreground colors are AA on their paired background.">
        <div className="ds-palette">
          {PRIORITY.map((s) => (
            <Swatch key={s.token} name={s.name} token={s.token} hex={s.hex} color={s.hex} />
          ))}
        </div>
      </SubSec>

      <SubSec
        title="Tags"
        desc="Stable per-tag rotation. Add new tags to the rotation; never invent ad-hoc colors at the call site."
      >
        <div className="ds-palette">
          {TAGS.map((s) => (
            <div key={s.name} className="ds-swatch">
              <div className="ds-swatch-color" style={{ background: s.bg }}>
                <span
                  style={{
                    background: s.bg,
                    color: s.hex,
                    padding: '4px 10px',
                    borderRadius: 5,
                    fontSize: 12,
                    fontWeight: 500,
                    position: 'relative',
                    zIndex: 1,
                  }}
                >
                  {s.name}
                </span>
              </div>
              <div className="ds-swatch-info">
                <div className="ds-swatch-name">{s.name}</div>
                <div className="ds-swatch-token">--ag-tag-{s.name.toLowerCase()}</div>
                <span className="ds-swatch-hex">
                  fg {s.hex} · bg {s.bg}
                </span>
              </div>
            </div>
          ))}
        </div>
      </SubSec>
    </Section>
  );
}
