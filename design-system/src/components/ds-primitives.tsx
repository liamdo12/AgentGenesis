import type { CSSProperties, ReactNode } from 'react';

type Theme = 'light' | 'dark';

export const Swatch = ({
  name,
  token,
  hex,
  color,
  dark = false,
}: {
  name: string;
  token: string;
  hex: string;
  color: string;
  dark?: boolean;
}) => (
  <div className="ds-swatch">
    <div className="ds-swatch-color" style={{ background: color }}>
      {dark && (
        <span
          style={{
            color: '#fff',
            fontFamily: 'Geist Mono',
            fontSize: 10,
            opacity: 0.7,
            position: 'relative',
            zIndex: 1,
          }}
        >
          {hex}
        </span>
      )}
    </div>
    <div className="ds-swatch-info">
      <div className="ds-swatch-name">{name}</div>
      <div className="ds-swatch-token">{token}</div>
      {!dark && <span className="ds-swatch-hex">{hex}</span>}
    </div>
  </div>
);

export const Section = ({
  id,
  title,
  anchor,
  children,
}: {
  id: string;
  title: string;
  anchor?: string;
  children: ReactNode;
}) => (
  <section id={id} className="ds-section">
    <header className="ds-section-head">
      <h2>{title}</h2>
      <span className="ds-anchor">#{anchor || id}</span>
    </header>
    {children}
  </section>
);

export const SubSec = ({
  title,
  code,
  desc,
  children,
}: {
  title: string;
  code?: string;
  desc?: string;
  children: ReactNode;
}) => (
  <div className="ds-subsec">
    <div className="ds-subsec-head">
      <h3>{title}</h3>
      {code && <code>{code}</code>}
      {desc && <p>{desc}</p>}
    </div>
    {children}
  </div>
);

export const Demo = ({
  label,
  dark,
  children,
  stack,
  bare,
}: {
  label: string;
  dark?: boolean;
  children: ReactNode;
  stack?: boolean;
  bare?: boolean;
}) => (
  <div className="ds-demo">
    <div className="ds-demo-head">
      <span className={'ds-dot ' + (dark ? 'is-dark' : 'is-light')} />
      <span style={{ marginLeft: 0 }}>{label}</span>
    </div>
    <div
      className={
        'ds-demo-body' +
        (stack ? ' is-stack' : '') +
        (dark ? ' is-dark' : '') +
        (bare ? ' is-bare' : '')
      }
    >
      {children}
    </div>
  </div>
);

export const Pair = ({ children }: { children: ReactNode }) => (
  <div className="ds-pair" style={{ position: 'relative' }}>
    {children}
  </div>
);

export const PairSide = ({
  theme = 'light',
  children,
  style,
}: {
  theme?: Theme;
  children: ReactNode;
  style?: CSSProperties;
}) => (
  <div style={{ background: theme === 'dark' ? '#0a0a0b' : '#ffffff', ...style }}>
    <span className="ds-pair-label" style={{ top: 10, left: 12 }}>
      {theme}
    </span>
    <div
      className="ag-app"
      data-theme={theme}
      data-density="compact"
      style={{ width: '100%', background: 'transparent' }}
    >
      {children}
    </div>
  </div>
);
