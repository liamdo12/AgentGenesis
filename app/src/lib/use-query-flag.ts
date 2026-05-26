import { useMemo } from 'react';

// Reads a `?name=1` query flag once at mount.
// Returns true iff the value is exactly "1". No subscription to URL changes.
export function useQueryFlag(name: string): boolean {
  return useMemo(() => {
    if (typeof window === 'undefined') return false;
    return new URLSearchParams(window.location.search).get(name) === '1';
  }, [name]);
}
