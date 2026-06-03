/**
 * Poll `GET /runs/{id}` with exponential backoff + jitter until the run reaches
 * a terminal status. Pauses while the tab is hidden and resumes on focus.
 *
 * `cancelled.current` mirrors the use-meetings pattern: when the consumer
 * switches `runId`, in-flight responses are discarded instead of overwriting
 * fresh state.
 */

import { useEffect, useRef, useState } from 'react';
import { apiJson } from '../auth';
import type { ApiRun } from '../lib/story-types';

const TERMINAL: ReadonlySet<ApiRun['status']> = new Set<ApiRun['status']>([
  'done',
  'failed',
  'pending_transcript',
]);

export type UseRunStatus = { run: ApiRun | null; error: string | null };

export function useRunStatus(runId: string | null): UseRunStatus {
  const [run, setRun] = useState<ApiRun | null>(null);
  const [error, setError] = useState<string | null>(null);
  const cancelled = useRef(false);

  useEffect(() => {
    cancelled.current = false;
    if (!runId) {
      return () => {
        cancelled.current = true;
      };
    }

    let attempt = 0;
    let timer: number | undefined;

    const tick = async () => {
      if (cancelled.current) return;
      try {
        const data = await apiJson<ApiRun>(`/runs/${runId}`);
        if (cancelled.current) return;
        setRun(data);
        setError(null);
        if (TERMINAL.has(data.status)) return;
      } catch (e) {
        if (cancelled.current) return;
        setError((e as Error).message);
      }
      const base = Math.min(1000 * Math.pow(1.5, attempt), 5000);
      const jitter = Math.random() * 400 - 200;
      attempt += 1;
      timer = window.setTimeout(tick, base + jitter);
    };

    if (!document.hidden) tick();
    const onVisibility = () => {
      if (document.hidden || cancelled.current) return;
      // Clear any pending tick before re-arming so visibility flips don't
      // stack parallel poll chains.
      if (timer !== undefined) {
        window.clearTimeout(timer);
        timer = undefined;
      }
      tick();
    };
    document.addEventListener('visibilitychange', onVisibility);

    return () => {
      cancelled.current = true;
      if (timer !== undefined) window.clearTimeout(timer);
      document.removeEventListener('visibilitychange', onVisibility);
    };
  }, [runId]);

  return { run, error };
}
