import { Pair, PairSide, Section, SubSec } from '../components/ds-primitives';
import { AgStoryCard } from '../components/ag-story-card';
import { AG_STORIES } from '../lib/seed-data';

const story = AG_STORIES[1];

export function StoryCardSection() {
  return (
    <Section id="story-card" title="Story card">
      <SubSec
        title="Anatomy"
        desc="Top: select + ID + title + priority. Middle: persona/want/benefit story. Mono-tagged AC line. Foot: tag, source, hover actions."
      >
        <div
          className="ag-app"
          data-theme="light"
          data-density="compact"
          style={{
            background: '#fbfbfa',
            padding: '40px 0',
            borderRadius: 10,
            border: '1px solid rgba(15,15,15,0.08)',
            display: 'grid',
            gridTemplateColumns: '140px minmax(0, 540px) 140px',
            gap: 0,
            justifyContent: 'center',
            alignItems: 'start',
            position: 'relative',
          }}
        >
          <div style={{ position: 'relative', height: '100%' }}>
            <div className="ds-co" style={{ position: 'absolute', right: 0, top: 8 }}>
              <b>1</b> ID · mono <i />
            </div>
            <div className="ds-co" style={{ position: 'absolute', right: 0, top: 30 }}>
              <b>2</b> Title <i />
            </div>
            <div className="ds-co" style={{ position: 'absolute', right: 0, top: 70 }}>
              <b>3</b> User story <i />
            </div>
            <div className="ds-co" style={{ position: 'absolute', right: 0, top: 116 }}>
              <b>4</b> AC · mono label <i />
            </div>
            <div className="ds-co" style={{ position: 'absolute', right: 0, bottom: 8 }}>
              <b>5</b> Tag · source <i />
            </div>
          </div>

          <div style={{ minWidth: 0 }}>
            <AgStoryCard story={story} />
          </div>

          <div style={{ position: 'relative', height: '100%' }}>
            <div className="ds-co" style={{ position: 'absolute', left: 0, top: 8 }}>
              <i /> <b>6</b> Priority pill
            </div>
            <div className="ds-co" style={{ position: 'absolute', left: 0, bottom: 8 }}>
              <i /> <b>7</b> Hover actions
            </div>
          </div>
        </div>
      </SubSec>

      <SubSec title="States" desc="Default · selected · approved.">
        <Pair>
          <PairSide theme="light">
            <div style={{ display: 'flex', flexDirection: 'column', gap: 8, width: '100%' }}>
              <AgStoryCard story={AG_STORIES[1]} />
              <AgStoryCard story={AG_STORIES[2]} selected />
              <AgStoryCard story={AG_STORIES[0]} approved />
            </div>
          </PairSide>
          <PairSide theme="dark">
            <div style={{ display: 'flex', flexDirection: 'column', gap: 8, width: '100%' }}>
              <AgStoryCard story={AG_STORIES[1]} />
              <AgStoryCard story={AG_STORIES[2]} selected />
              <AgStoryCard story={AG_STORIES[0]} approved />
            </div>
          </PairSide>
        </Pair>
      </SubSec>

      <SubSec
        title="Styles"
        code='cardStyle="bordered | flat | hairline"'
        desc="Exposed via the Tweaks panel. Pick by display density: bordered for default lists; flat for grouped lanes; hairline for very long backlogs."
      >
        <Pair>
          <PairSide theme="light">
            <div style={{ display: 'flex', flexDirection: 'column', gap: 0, width: '100%' }}>
              <AgStoryCard story={AG_STORIES[1]} cardStyle="bordered" />
              <div style={{ height: 12 }} />
              <AgStoryCard story={AG_STORIES[2]} cardStyle="flat" />
              <div style={{ height: 12 }} />
              <AgStoryCard story={AG_STORIES[3]} cardStyle="hairline" />
            </div>
          </PairSide>
          <PairSide theme="dark">
            <div style={{ display: 'flex', flexDirection: 'column', gap: 0, width: '100%' }}>
              <AgStoryCard story={AG_STORIES[1]} cardStyle="bordered" />
              <div style={{ height: 12 }} />
              <AgStoryCard story={AG_STORIES[2]} cardStyle="flat" />
              <div style={{ height: 12 }} />
              <AgStoryCard story={AG_STORIES[3]} cardStyle="hairline" />
            </div>
          </PairSide>
        </Pair>
      </SubSec>
    </Section>
  );
}
