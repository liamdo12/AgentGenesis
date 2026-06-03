/**
 * Server-persisted approval state per run.
 *
 * Click → optimistic display via `pendingChanges`. After 250ms the hook POSTs
 * the buffered delta; clicks during the in-flight POST stay queued and fire
 * in a follow-up POST (race-safe reconcile — Red Team F7). On POST failure,
 * only the failing batch reverts; subsequent clicks keep their optimistic
 * state.
 */

import { useCallback, useEffect, useMemo, useRef, useState } from 'react';
import { ApiError, apiJson } from '../auth';

const DEBOUNCE_MS = 250;

export type UseApprovals = {
  approved: Set<string>;
  toggle: (storyId: string) => void;
  bulkApprove: (storyIds: string[]) => void;
  reload: () => void;
  error: string | null;
};

export function useApprovals(runId: string | null): UseApprovals {
  const [approved, setApproved] = useState<Set<string>>(new Set());
  const [pendingChanges, setPendingChanges] = useState<Map<string, boolean>>(new Map());
  const [error, setError] = useState<string | null>(null);
  const [version, setVersion] = useState(0);
  const cancelled = useRef(false);
  const flushTimer = useRef<number | undefined>(undefined);
  const inFlight = useRef(false);
  const pendingRef = useRef(pendingChanges);
  pendingRef.current = pendingChanges;

  // Initial fetch / reload on runId change.
  useEffect(() => {
    cancelled.current = false;
    setError(null);
    setApproved(new Set());
    if (!runId) return () => { cancelled.current = true; };

    apiJson<{ approved_ids: string[] }>(`/runs/${runId}/stories/approvals`)
      .then((data) => {
        if (cancelled.current) return;
        setApproved((prev) => {
          // If the user has clicked during the fetch, those clicks own the ids
          // they touched; don't overwrite them with stale server state.
          const next = new Set(data.approved_ids);
          for (const [id, v] of pendingRef.current) {
            if (v) next.add(id);
            else next.delete(id);
          }
          // Resync approved with the merged view; pending stays intact.
          void prev;
          return next;
        });
      })
      .catch((e) => {
        if (cancelled.current) return;
        const msg = e instanceof ApiError
          ? `${e.status}: ${(e.body as { detail?: string })?.detail ?? e.message}`
          : (e as Error).message;
        setError(msg);
      });

    return () => {
      cancelled.current = true;
      if (flushTimer.current !== undefined) window.clearTimeout(flushTimer.current);
    };
  }, [runId, version]);

  const flush = useCallback(async () => {
    if (!runId || inFlight.current) return;
    const batch = new Map(pendingRef.current);
    if (batch.size === 0) return;
    inFlight.current = true;
    try {
      const changes = Object.fromEntries(batch);
      const res = await apiJson<{ approved_ids: string[] }>(
        `/runs/${runId}/stories/approvals`,
        {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({ changes }),
        },
      );
      if (cancelled.current) return;
      const serverSet = new Set(res.approved_ids);
      setPendingChanges((prev) => {
        const next = new Map(prev);
        for (const id of batch.keys()) next.delete(id);
        return next;
      });
      // Reconcile: server set + any clicks added during the flight.
      setApproved(() => {
        const merged = new Set(serverSet);
        const remaining = new Map(pendingRef.current);
        for (const id of batch.keys()) remaining.delete(id);
        for (const [id, v] of remaining) {
          if (v) merged.add(id);
          else merged.delete(id);
        }
        return merged;
      });
      setError(null);
    } catch (e) {
      if (cancelled.current) return;
      // Revert just the failing batch.
      setPendingChanges((prev) => {
        const next = new Map(prev);
        for (const id of batch.keys()) next.delete(id);
        return next;
      });
      const msg = e instanceof ApiError
        ? `${e.status}: ${(e.body as { detail?: string })?.detail ?? e.message}`
        : (e as Error).message;
      setError(msg);
    } finally {
      inFlight.current = false;
      // If new clicks arrived during the POST, schedule another flush.
      if (pendingRef.current.size > 0) {
        if (flushTimer.current !== undefined) window.clearTimeout(flushTimer.current);
        flushTimer.current = window.setTimeout(flush, DEBOUNCE_MS);
      }
    }
  }, [runId]);

  const scheduleFlush = useCallback(() => {
    if (flushTimer.current !== undefined) window.clearTimeout(flushTimer.current);
    flushTimer.current = window.setTimeout(flush, DEBOUNCE_MS);
  }, [flush]);

  const toggle = useCallback((storyId: string) => {
    setPendingChanges((prev) => {
      const next = new Map(prev);
      const display = approved.has(storyId) || prev.get(storyId) === true;
      const desired = !display;
      next.set(storyId, desired);
      return next;
    });
    scheduleFlush();
  }, [approved, scheduleFlush]);

  const bulkApprove = useCallback((storyIds: string[]) => {
    setPendingChanges((prev) => {
      const next = new Map(prev);
      for (const id of storyIds) next.set(id, true);
      return next;
    });
    scheduleFlush();
  }, [scheduleFlush]);

  // Optimistic display = server-confirmed ∪ pending clicks.
  const displayApproved = useMemo(() => {
    const s = new Set(approved);
    for (const [id, v] of pendingChanges) {
      if (v) s.add(id);
      else s.delete(id);
    }
    return s;
  }, [approved, pendingChanges]);

  return {
    approved: displayApproved,
    toggle,
    bulkApprove,
    reload: () => setVersion((v) => v + 1),
    error,
  };
}
