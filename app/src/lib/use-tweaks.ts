import { useCallback, useState } from 'react';

export type Tweaks = {
  theme: 'light' | 'dark';
  density: 'compact' | 'comfortable';
  cardStyle: 'bordered' | 'flat' | 'hairline';
};

export const DEFAULT_TWEAKS: Tweaks = {
  theme: 'light',
  density: 'compact',
  cardStyle: 'bordered',
};

type SetTweak = <K extends keyof Tweaks>(key: K, value: Tweaks[K]) => void;

export function useTweaks(initial: Tweaks = DEFAULT_TWEAKS): [Tweaks, SetTweak] {
  const [t, setT] = useState<Tweaks>(initial);
  const set = useCallback<SetTweak>((key, value) => {
    setT((prev) => ({ ...prev, [key]: value }));
  }, []);
  return [t, set];
}
