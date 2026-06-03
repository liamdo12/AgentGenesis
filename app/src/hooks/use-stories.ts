/**
 * Fetch the run's stories.json once the run is in `done`. Provides a
 * `setStories` setter so chat-driven revisions (Phase 7) can hot-swap
 * the in-memory list without a round-trip.
 */

import { useCallback, useEffect, useRef, useState } from 'react';
import { ApiError, apiJson } from '../auth';
import type { StoriesOutput, Story } from '../lib/story-types';

export type UseStories = {
  stories: Story[];
  loading: boolean;
  error: string | null;
  setStories: (next: Story[]) => void;
  reload: () => void;
};

export function useStories(runId: string | null): UseStories {
  const [stories, setStoriesState] = useState<Story[]>([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [version, setVersion] = useState(0);
  const cancelled = useRef(false);

  useEffect(() => {
    cancelled.current = false;
    if (!runId) {
      setStoriesState([]);
      return () => {
        cancelled.current = true;
      };
    }
    setLoading(true);
    setError(null);
    apiJson<StoriesOutput>(`/runs/${runId}/files/stories.json`)
      .then((data) => {
        if (cancelled.current) return;
        setStoriesState(data.stories);
      })
      .catch((e) => {
        if (cancelled.current) return;
        const msg = e instanceof ApiError
          ? `${e.status}: ${(e.body as { detail?: string })?.detail ?? e.message}`
          : (e as Error).message;
        setError(msg);
      })
      .finally(() => {
        if (cancelled.current) return;
        setLoading(false);
      });
    return () => {
      cancelled.current = true;
    };
  }, [runId, version]);

  const setStories = useCallback((next: Story[]) => {
    setStoriesState(next);
  }, []);

  return {
    stories,
    loading,
    error,
    setStories,
    reload: () => setVersion((v) => v + 1),
  };
}
