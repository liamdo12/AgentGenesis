import { useEffect, useState } from 'react';
import { Icon } from '@ds/lib/icons';
import { useRunLifecycle } from '../hooks/use-run-lifecycle';
import { useAppDispatch, useAppState } from '../state/app-state-context';
import { AiSidePanel } from './ai-side-panel';
import { MeetingsEmpty } from './meetings-empty';
import { MeetingsExtracting } from './meetings-extracting';
import { MeetingsList } from './meetings-list';
import { MobileTabBar, type MobileTab } from './mobile-tab-bar';

export function StoriesPanel() {
  const { stories, approved, selectedMeetingId } = useAppState();
  const dispatch = useAppDispatch();
  const {
    runId,
    run,
    stories: serverStories,
    setStories,
    startExtraction,
    error,
  } = useRunLifecycle(selectedMeetingId);
  const [mobileTab, setMobileTab] = useState<MobileTab>('stories');

  // Sync the lifecycle hook into app state so panels that read from
  // useAppState() (rather than the hook) stay consistent.
  useEffect(() => {
    dispatch({ type: 'SET_ACTIVE_RUN', payload: runId });
  }, [runId, dispatch]);
  useEffect(() => {
    dispatch({ type: 'SET_STORIES_FROM_SERVER', payload: serverStories });
  }, [serverStories, dispatch]);
  useEffect(() => {
    if (!run) return;
    if (run.status === 'done') {
      dispatch({ type: 'RUN_DONE', payload: run });
    } else if (run.status === 'failed') {
      dispatch({ type: 'RUN_FAILED', payload: { error: run.error ?? 'extraction failed' } });
    } else {
      dispatch({ type: 'RUN_PROGRESS', payload: run });
    }
  }, [run, dispatch]);

  const isExtracting = run !== null && run.status !== 'done' && run.status !== 'failed' && run.status !== 'pending_transcript';

  const body = isExtracting
    ? <MeetingsExtracting />
    : stories.length === 0
      ? <MeetingsEmpty onStartExtraction={startExtraction} loading={isExtracting} error={error} />
      : <MeetingsList />;

  const pendingCount = stories.filter((s) => !approved.has(s.id)).length;

  return (
    <>
      <MobileTabBar active={mobileTab} onPick={setMobileTab} pendingCount={pendingCount} />
      <div className="ag-main" data-mobile-tab={mobileTab} style={{ position: 'relative' }}>
        {body}
        <AiSidePanel onRevision={setStories} />
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
