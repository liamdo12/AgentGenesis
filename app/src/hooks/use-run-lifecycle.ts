/**
 * Compose useRunForMeeting + useRunStatus + useStories into a single hook
 * that StoriesPanel can consume directly.
 */

import { useEffect, useState } from 'react';
import { useRunForMeeting } from './use-run-for-meeting';
import { useRunStatus } from './use-run-status';
import { useStories } from './use-stories';

export function useRunLifecycle(meetingId: string | null) {
  const { run: terminalRun, startExtraction, refresh: refreshList, loading: listLoading, error: listError } = useRunForMeeting(meetingId);
  // Active run-id we follow: either the terminal one for this meeting OR the
  // run we just kicked off via `startExtraction`. Cleared when meeting changes.
  const [activeRunId, setActiveRunId] = useState<string | null>(null);

  useEffect(() => {
    setActiveRunId(terminalRun?.id ?? null);
  }, [terminalRun?.id]);

  const { run: liveRun, error: pollError } = useRunStatus(activeRunId);
  const finalRunId = liveRun?.status === 'done' ? activeRunId : null;
  const { stories, loading: storiesLoading, error: storiesError, setStories, reload: reloadStories } = useStories(finalRunId);

  const start = async () => {
    const id = await startExtraction();
    if (id) {
      setActiveRunId(id);
      refreshList();
    }
    return id;
  };

  return {
    runId: activeRunId,
    run: liveRun ?? terminalRun,
    stories,
    setStories,
    startExtraction: start,
    reloadStories,
    refresh: refreshList,
    loading: listLoading || storiesLoading,
    error: pollError ?? listError ?? storiesError,
  };
}
