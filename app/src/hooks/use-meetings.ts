// Fetch the user's Teams meetings from the backend `/meetings` endpoint.
//
// Plain useEffect+useState (no TanStack Query) — YAGNI for v1. Per red-team
// Finding 12, fetch lives here (or in panels) NOT inside MeetingDropdown.
//
// Returns the same shape as the existing `Meeting` seed type so panels can
// keep their prop interface.

import { useEffect, useRef, useState } from 'react';
import type { Meeting } from '@ds/lib/seed-data';
import { ApiError, apiJson, useActiveAccount } from '../auth';

type ApiMeeting = {
  id: string;
  title: string;
  organizer: string;
  start_iso: string;
  duration_sec: number;
};

function toMeeting(m: ApiMeeting): Meeting {
  // Render backend `start_iso` into the dropdown's "Aug 22 · 42 min" form.
  const start = new Date(m.start_iso);
  const month = start.toLocaleString('en-US', { month: 'short' });
  const detail = `${month} ${start.getDate()} · ${Math.round(m.duration_sec / 60)} min`;
  return {
    id: m.id,
    title: m.title,
    detail,
    candidates: 0,
  };
}

export type UseMeetings = {
  meetings: Meeting[];
  loading: boolean;
  error: string | null;
  reload: () => void;
};

export function useMeetings(): UseMeetings {
  const [meetings, setMeetings] = useState<Meeting[]>([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [version, setVersion] = useState(0);
  const { isAuthenticated } = useActiveAccount();
  const cancelled = useRef(false);

  useEffect(() => {
    cancelled.current = false;
    if (!isAuthenticated) {
      setMeetings([]);
      setLoading(false);
      setError(null);
      return () => {
        cancelled.current = true;
      };
    }
    setLoading(true);
    setError(null);
    apiJson<ApiMeeting[]>('/meetings')
      .then((data) => {
        if (cancelled.current) return;
        setMeetings(data.map(toMeeting));
      })
      .catch((e) => {
        if (cancelled.current) return;
        setError(e instanceof ApiError ? `${e.status}: ${(e.body as { detail?: string })?.detail ?? e.message}` : (e as Error).message);
      })
      .finally(() => {
        if (cancelled.current) return;
        setLoading(false);
      });
    return () => {
      cancelled.current = true;
    };
  }, [isAuthenticated, version]);

  return { meetings, loading, error, reload: () => setVersion((v) => v + 1) };
}
