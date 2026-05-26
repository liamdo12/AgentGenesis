import { useState } from 'react';
import { Icon } from '@ds/lib/icons';
import { useAppState } from '../state/app-state-context';
import { AiSidePanel } from './ai-side-panel';
import { MeetingsEmpty } from './meetings-empty';
import { MeetingsExtracting } from './meetings-extracting';
import { MeetingsList } from './meetings-list';
import { MobileTabBar, type MobileTab } from './mobile-tab-bar';

export function StoriesPanel() {
  const { stories, phase, approved } = useAppState();
  const [mobileTab, setMobileTab] = useState<MobileTab>('stories');

  const body =
    stories.length === 0 ? <MeetingsEmpty /> :
    phase === 'extracting' ? <MeetingsExtracting /> :
    <MeetingsList />;

  const pendingCount = stories.filter((s) => !approved.has(s.id)).length;

  return (
    <>
      <MobileTabBar active={mobileTab} onPick={setMobileTab} pendingCount={pendingCount} />
      <div className="ag-main" data-mobile-tab={mobileTab} style={{ position: 'relative' }}>
        {body}
        <AiSidePanel />
        {mobileTab === 'stories' && (
          <button
            type="button"
            className="ag-mobile-fab"
            title="Ask Claude"
            onClick={() => setMobileTab('assistant')}
          >
            <Icon.Sparkle width={18} height={18} />
          </button>
        )}
      </div>
    </>
  );
}
