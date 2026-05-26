import { Section, SubSec } from '../components/ds-primitives';

const SCALE = [
  { name: 'Display',    meta: '36 / 1.1 · -0.025em / 600',     size: 36,   weight: 600, ls: '-0.025em', sample: 'Agent Genesis' },
  { name: 'Title',      meta: '22 / 1.2 · -0.018em / 600',     size: 22,   weight: 600, ls: '-0.018em', sample: 'Stories from Sprint Planning' },
  { name: 'Section',    meta: '17 / 1.2 · -0.015em / 600',     size: 17,   weight: 600, ls: '-0.015em', sample: 'Acceptance criteria' },
  { name: 'Card title', meta: '14 / 1.35 · -0.01em / 600',     size: 14,   weight: 600, ls: '-0.01em',  sample: 'User authentication with SSO' },
  { name: 'Body',       meta: '13 / 1.45 · -0em / 400',        size: 13,   weight: 400, ls: '0',
    sample: "As a corporate user, I want to log in using my company SSO so that I don't manage separate credentials." },
  { name: 'Caption',    meta: '11.5 / 1.4 · 0em / 400',        size: 11.5, weight: 400, ls: '0',
    sample: 'Sprint Planning · Aug 22 · last extracted 8 min ago' },
  {
    name: 'Eyebrow',
    meta: '10.5 / 1.2 · 0.05em / 600 · mono',
    size: 10.5,
    weight: 600,
    ls: '0.05em',
    sample: 'AC · CONTEXT · SUGGESTED',
    mono: true,
    upper: true,
  },
];

export function TypographySection() {
  return (
    <Section id="typography" title="Typography">
      <SubSec
        title="Family"
        desc="Geist for UI, Geist Mono for identifiers (story IDs, AC labels, tokens, keyboard shortcuts). Avoid mixing weights below 400."
      >
        <div className="ds-cards" style={{ gridTemplateColumns: '1fr 1fr' }}>
          <div className="ds-card">
            <div className="ds-card-label">Sans · Geist</div>
            <div style={{ fontSize: 28, fontWeight: 600, letterSpacing: '-0.02em', marginBottom: 6 }}>
              Aa Bb Cc 0123
            </div>
            <div style={{ fontSize: 12, color: '#71717a' }}>400 · 500 · 600 · 700</div>
          </div>
          <div className="ds-card">
            <div className="ds-card-label">Mono · Geist Mono</div>
            <div
              style={{
                fontFamily: 'Geist Mono, monospace',
                fontSize: 24,
                fontWeight: 500,
                letterSpacing: '-0.01em',
                marginBottom: 6,
              }}
            >
              AG-024 / 0123
            </div>
            <div style={{ fontSize: 12, color: '#71717a', fontFamily: 'Geist Mono, monospace' }}>400 · 500</div>
          </div>
        </div>
      </SubSec>

      <SubSec title="Scale" desc="Sizes are halved past 14px to stay legible in dense contexts (cards, AI rail).">
        <div className="ds-demo">
          <div className="ds-demo-body is-stack" style={{ gap: 0, padding: '0 24px' }}>
            {SCALE.map((s) => (
              <div key={s.name} className="ds-type">
                <span className="ds-type-name">{s.name}</span>
                <span className="ds-type-meta">{s.meta}</span>
                <span
                  style={{
                    fontSize: s.size,
                    fontWeight: s.weight,
                    letterSpacing: s.ls,
                    fontFamily: s.mono ? 'Geist Mono, monospace' : 'Geist, sans-serif',
                    textTransform: s.upper ? 'uppercase' : 'none',
                    color: '#18181b',
                    lineHeight: 1.3,
                  }}
                >
                  {s.sample}
                </span>
              </div>
            ))}
          </div>
        </div>
      </SubSec>
    </Section>
  );
}
