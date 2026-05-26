import { Section, SubSec } from '../components/ds-primitives';
import { Icon } from '../lib/icons';
import { ICON_SET } from '../lib/seed-data';

export function IconsSection() {
  return (
    <Section id="iconography" title="Iconography">
      <SubSec
        title="Line · 14×14 · 1.6 stroke"
        desc="One weight, one size, currentColor. Use sparingly — text labels are preferred to icons. Never decorate."
      >
        <div className="ds-demo">
          <div className="ds-demo-body" style={{ gap: 8, alignItems: 'flex-start' }}>
            {ICON_SET.map((name) => {
              const Ic = Icon[name];
              if (!Ic) return null;
              return (
                <div
                  key={name}
                  style={{
                    display: 'flex',
                    flexDirection: 'column',
                    alignItems: 'center',
                    gap: 6,
                    width: 70,
                  }}
                >
                  <div
                    style={{
                      width: 36,
                      height: 36,
                      border: '1px solid rgba(15,15,15,0.08)',
                      borderRadius: 6,
                      display: 'flex',
                      alignItems: 'center',
                      justifyContent: 'center',
                      color: '#52525b',
                    }}
                  >
                    <Ic />
                  </div>
                  <span style={{ fontFamily: 'Geist Mono, monospace', fontSize: 10, color: '#71717a' }}>
                    {name}
                  </span>
                </div>
              );
            })}
          </div>
        </div>
      </SubSec>
    </Section>
  );
}
