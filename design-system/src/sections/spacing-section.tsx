import { Section, SubSec } from '../components/ds-primitives';

const SPACING = [2, 4, 6, 8, 10, 12, 14, 16, 20, 24, 32, 40];

const RADII = [
  { r: 4, n: 'sm' },
  { r: 6, n: 'md' },
  { r: 8, n: 'lg' },
  { r: 10, n: 'xl' },
  { r: 12, n: '2xl' },
  { r: 999, n: 'full' },
];

const SHADOWS = [
  { token: '--ag-shadow-sm', shadow: '0 1px 2px rgba(15,15,15,0.04)' },
  { token: '--ag-shadow',    shadow: '0 1px 2px rgba(15,15,15,0.04), 0 8px 24px -8px rgba(15,15,15,0.06)' },
  { token: '--ag-shadow-lg', shadow: '0 1px 2px rgba(15,15,15,0.06), 0 24px 64px -16px rgba(15,15,15,0.14)' },
];

export function SpacingSection() {
  return (
    <Section id="spacing" title="Spacing, radii, shadow">
      <SubSec
        title="Spacing"
        desc="Multiples of 2px from 2 up to 16, then jump to 20 / 24 / 32 / 40 for layout-level rhythm."
      >
        <div className="ds-demo">
          <div className="ds-demo-body" style={{ alignItems: 'flex-end', padding: '24px 32px' }}>
            {SPACING.map((n) => (
              <div key={n} style={{ display: 'flex', flexDirection: 'column', alignItems: 'center', gap: 6 }}>
                <div style={{ width: n, height: n, background: '#5b53e8', borderRadius: 1 }} />
                <span style={{ fontFamily: 'Geist Mono, monospace', fontSize: 10, color: '#71717a' }}>{n}</span>
              </div>
            ))}
          </div>
        </div>
      </SubSec>

      <SubSec
        title="Radii"
        desc="4px for inline pills and tags · 6–7 for buttons and chips · 8–9 for cards and inputs · 10–12 for modals and large containers."
      >
        <div className="ds-demo">
          <div className="ds-demo-body">
            <div className="ds-radii">
              {RADII.map((s) => (
                <div key={s.r}>
                  <i style={{ borderRadius: s.r }} />
                  <span>
                    {s.n} · {s.r === 999 ? 'pill' : `${s.r}px`}
                  </span>
                </div>
              ))}
            </div>
          </div>
        </div>
      </SubSec>

      <SubSec
        title="Shadow"
        desc="Light theme uses near-black tinted shadows; dark theme drops them in favor of border-only elevation."
      >
        <div className="ds-shadows">
          {SHADOWS.map((s) => (
            <div key={s.token}>
              <i style={{ boxShadow: s.shadow }} />
              <span>{s.token}</span>
            </div>
          ))}
        </div>
      </SubSec>
    </Section>
  );
}
