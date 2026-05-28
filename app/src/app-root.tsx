import { AgTopBar } from '@ds/components/ag-topbar';
import { Icon } from '@ds/lib/icons';
import { useActiveAccount } from './auth';
import { AuthButton } from './components/auth-button';
import { TweaksPanel } from './components/tweaks-panel';
import { DashboardPanel } from './panels/dashboard-panel';
import { StoriesPanel } from './panels/stories-panel';
import { ModalHost } from './modals/modal-host';
import { useQueryFlag } from './lib/use-query-flag';
import { useAppDispatch, useAppState } from './state/app-state-context';
import type { Tweaks } from './lib/use-tweaks';
import type { Action } from './state/app-state-types';

export function AppRoot() {
  const state = useAppState();
  const dispatch = useAppDispatch();
  // ?tweaks=1 exposes the design-QA panel. Hidden by default.
  const tweaksOn = useQueryFlag('tweaks');
  const { isAuthenticated } = useActiveAccount();

  const isDark = state.tweaks.theme === 'dark';
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
        right={
          <>
            {isDark !== undefined && (
              <button
                type="button"
                className="ag-iconbtn"
                onClick={() => setTweak('theme', isDark ? 'light' : 'dark')}
                title="Toggle theme"
              >
                {isDark ? <Icon.Sun /> : <Icon.Moon />}
              </button>
            )}
            <AuthButton />
          </>
        }
      />
      {isAuthenticated ? (
        state.topTab === 'Dashboard' ? <DashboardPanel /> : <StoriesPanel />
      ) : (
        <UnauthenticatedNotice />
      )}
      <ModalHost />
      {tweaksOn && <TweaksPanel t={state.tweaks} setTweak={setTweak} />}
    </div>
  );
}

function UnauthenticatedNotice() {
  return (
    <div className="ag-empty" style={{ paddingTop: 80 }}>
      <div className="ag-empty-icon" style={{ width: 64, height: 64, borderRadius: 16 }}>
        <Icon.Calendar width={24} height={24} />
      </div>
      <div className="ag-empty-title">Sign in to continue</div>
      <div className="ag-empty-sub">
        Use your Microsoft work account to access your Teams meeting recordings.
        Dev sessions can append <code>?fakeAuth=1</code> to the URL.
      </div>
    </div>
  );
}
