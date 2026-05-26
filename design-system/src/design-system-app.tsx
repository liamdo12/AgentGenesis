import { DsSidebarNav } from './components/ds-sidebar-nav';
import { ColorsSection } from './sections/colors-section';
import { TypographySection } from './sections/typography-section';
import { SpacingSection } from './sections/spacing-section';
import { IconsSection } from './sections/icons-section';
import { ButtonsSection } from './sections/buttons-section';
import { ChipsSection } from './sections/chips-section';
import { InputsSection } from './sections/inputs-section';
import { StoryCardSection } from './sections/story-card-section';
import { NavSection } from './sections/nav-section';
import { BulkBarSection } from './sections/bulk-bar-section';
import { AIPanelSection } from './sections/ai-panel-section';
import { ModalSection } from './sections/modal-section';
import { StatsRoadmapSection } from './sections/stats-roadmap-section';
import { EmptyStateSection } from './sections/empty-state-section';

export function DesignSystemApp() {
  return (
    <div className="ds-shell">
      <DsSidebarNav />
      <main className="ds-main">
        <section id="overview" className="ds-hero">
          <div className="ds-eyebrow">Design system · v0.1</div>
          <h1>Agent Genesis</h1>
          <p>
            A restrained, type-led system for triaging meeting transcripts into ship-ready user stories.
            Hairline borders, a single indigo accent, mono-set identifiers, and a Claude-attributed purple
            reserved exclusively for AI surfaces. Light + dark are first-class.
          </p>
          <div className="ds-hero-meta">
            <div>
              <span>Family</span>
              <span>Geist · Geist Mono</span>
            </div>
            <div>
              <span>Accent</span>
              <span style={{ display: 'inline-flex', alignItems: 'center', gap: 6 }}>
                <i style={{ width: 12, height: 12, borderRadius: 3, background: '#5b53e8' }} /> #5b53e8
              </span>
            </div>
            <div>
              <span>Themes</span>
              <span>Light · Dark</span>
            </div>
            <div>
              <span>Density</span>
              <span>Compact · Comfortable</span>
            </div>
          </div>
        </section>

        <ColorsSection />
        <TypographySection />
        <SpacingSection />
        <IconsSection />
        <ButtonsSection />
        <ChipsSection />
        <InputsSection />
        <StoryCardSection />
        <NavSection />
        <BulkBarSection />
        <AIPanelSection />
        <ModalSection />
        <StatsRoadmapSection />
        <EmptyStateSection />

        <footer className="ds-footer">
          <span>Agent Genesis · Design system v0.1</span>
          <span>·</span>
          <span>Light + dark · Compact + comfortable</span>
        </footer>
      </main>
    </div>
  );
}
