import { AgTopBar } from '@ds/components/ag-topbar';
import { StoriesPanel } from './panels/stories-panel';
import { DashboardPanel } from './panels/dashboard-panel';
import { ModalHost } from './modals/modal-host';
import { TweaksPanel } from './components/tweaks-panel';
import { useQueryFlag } from './lib/use-query-flag';
import { useAppDispatch, useAppState } from './state/app-state-context';
import type { Action } from './state/app-state-types';
import type { Tweaks } from './lib/use-tweaks';

export function AppRoot() {
  const state = useAppState();
  const dispatch = useAppDispatch();
  // ?tweaks=1 exposes the design-QA panel. Hidden by default.
  const tweaksOn = useQueryFlag('tweaks');

  const isDark = state.tweaks.theme === 'dark';
  // TS can't track the K binding through the literal back to the discriminated
  // payload union, so we narrow at the boundary.
  const setTweak = <K extends keyof Tweaks>(key: K, value: Tweaks[K]) =>
    dispatch({
      type: 'SET_TWEAK',
      payload: { key, value } as Extract<Action, { type: 'SET_TWEAK' }>['payload'],
    });

  return (
    <div className="ag-app" data-theme={state.tweaks.theme} data-density={state.tweaks.density}>
      <AgTopBar
        activeTab={state.topTab}
        onTab={(id) => dispatch({ type: 'SET_TOP_TAB', payload: id })}
        dark={isDark}
        onToggleDark={() => setTweak('theme', isDark ? 'light' : 'dark')}
      />
      {state.topTab === 'Dashboard' ? <DashboardPanel /> : <StoriesPanel />}
      <ModalHost />
      {tweaksOn && <TweaksPanel t={state.tweaks} setTweak={setTweak} />}
    </div>
  );
}
