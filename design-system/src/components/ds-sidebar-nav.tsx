import { Fragment, useEffect, useState } from 'react';

const NAV: { group: string; items: { id: string; label: string }[] }[] = [
  {
    group: 'Start',
    items: [{ id: 'overview', label: 'Overview' }],
  },
  {
    group: 'Foundations',
    items: [
      { id: 'colors',       label: 'Color' },
      { id: 'typography',   label: 'Typography' },
      { id: 'spacing',      label: 'Space · radius · shadow' },
      { id: 'iconography',  label: 'Iconography' },
    ],
  },
  {
    group: 'Atoms',
    items: [
      { id: 'buttons',    label: 'Buttons' },
      { id: 'chips-tags', label: 'Chips, tags, pills' },
      { id: 'inputs',     label: 'Inputs' },
    ],
  },
  {
    group: 'Patterns',
    items: [
      { id: 'story-card',    label: 'Story card' },
      { id: 'nav',           label: 'Top bar & tabs' },
      { id: 'bulk-bar',      label: 'Bulk toolbar' },
      { id: 'ai-panel',      label: 'AI assistant' },
      { id: 'modal',         label: 'Modal' },
      { id: 'stats-roadmap', label: 'Stats & roadmap' },
      { id: 'empty-state',   label: 'Empty state' },
    ],
  },
];

export function DsSidebarNav() {
  const [active, setActive] = useState('overview');

  useEffect(() => {
    const ids = NAV.flatMap((g) => g.items.map((i) => i.id));
    const els = ids
      .map((id) => document.getElementById(id))
      .filter((el): el is HTMLElement => el !== null);
    const io = new IntersectionObserver(
      (entries) => {
        const visible = entries.filter((e) => e.isIntersecting);
        if (visible.length) {
          visible.sort((a, b) => a.boundingClientRect.top - b.boundingClientRect.top);
          setActive(visible[0].target.id);
        }
      },
      { rootMargin: '-10% 0px -70% 0px' },
    );
    els.forEach((el) => io.observe(el));
    return () => io.disconnect();
  }, []);

  return (
    <aside className="ds-nav">
      <div className="ds-nav-brand">
        <span className="ds-nav-brand-mark">AG</span>
        <div className="ds-nav-brand-text">
          <b>Agent Genesis</b>
          <span>Design system · v0.1</span>
        </div>
      </div>
      {NAV.map((g) => (
        <Fragment key={g.group}>
          <div className="ds-nav-group">{g.group}</div>
          {g.items.map((it) => (
            <a key={it.id} href={`#${it.id}`} className={active === it.id ? 'is-active' : ''}>
              {it.label} <span>↗</span>
            </a>
          ))}
        </Fragment>
      ))}
    </aside>
  );
}
