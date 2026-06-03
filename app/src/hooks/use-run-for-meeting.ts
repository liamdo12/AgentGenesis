/**
 * Find the most recent terminal run for a meeting, or expose `startExtraction`.
 *
 * Calls `GET /runs?limit=100`, filters client-side by meeting_id (the backend
 * doesn't yet take a meeting_id query param). Newest first; picks the first
 * `done` / `failed` / `pending_transcript` entry.
 */

import { useCallback, useEffect, useRef, useState } from 'react';
import { ApiError, apiJson, useActiveAccount } from '../auth';
import type { ApiRun } from '../lib/story-types';

const TERMINAL: ReadonlySet<ApiRun['status']> = new Set<ApiRun['status']>([
  'done',
  'failed',
  'pending_transcript',
]);

export type UseRunForMeeting = {
  run: ApiRun | null;
  loading: boolean;
  error: string | null;
  startExtraction: () => Promise<string | null>;
  refresh: () => void;
};

export function useRunForMeeting(meetingId: string | null): UseRunForMeeting {
  const [run, setRun] = useState<ApiRun | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [version, setVersion] = useState(0);
  const { isAuthenticated } = useActiveAccount();
  const cancelled = useRef(false);

  useEffect(() => {
    cancelled.current = false;
    setRun(null);
    if (!meetingId || !isAuthenticated) {
      setLoading(false);
      return () => {
        cancelled.current = true;
      };
    }
    setLoading(true);
    setError(null);
    apiJson<ApiRun[]>('/runs?limit=100')
      .then((data) => {
        if (cancelled.current) return;
        const match = data.find((r) => r.meeting_id === meetingId && TERMINAL.has(r.status));
        setRun(match ?? null);
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
  }, [meetingId, isAuthenticated, version]);

  const startExtraction = useCallback(async (): Promise<string | null> => {
    if (!meetingId) return null;
    try {
      const res = await apiJson<{ run_id: string }>('/runs', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ meeting_id: meetingId }),
      });
      return res.run_id;
    } catch (e) {
      const msg = e instanceof ApiError
        ? `${e.status}: ${(e.body as { detail?: string })?.detail ?? e.message}`
        : (e as Error).message;
      setError(msg);
      return null;
    }
  }, [meetingId]);

  return {
    run,
    loading,
    error,
    startExtraction,
    refresh: () => setVersion((v) => v + 1),
  };
}
