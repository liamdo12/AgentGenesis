import { createContext, useContext, useReducer, type Dispatch, type ReactNode } from 'react';
import { initialState, reducer } from './app-state-reducer';
import type { Action, AppState } from './app-state-types';

const AppStateContext = createContext<AppState | null>(null);
const AppDispatchContext = createContext<Dispatch<Action> | null>(null);

export function AppStateProvider({ children }: { children: ReactNode }) {
  const [state, dispatch] = useReducer(reducer, undefined, initialState);
  return (
    <AppStateContext.Provider value={state}>
      <AppDispatchContext.Provider value={dispatch}>{children}</AppDispatchContext.Provider>
    </AppStateContext.Provider>
  );
}

export function useAppState(): AppState {
  const ctx = useContext(AppStateContext);
  if (ctx === null) {
    throw new Error('useAppState must be used inside <AppStateProvider>');
  }
  return ctx;
}

export function useAppDispatch(): Dispatch<Action> {
  const ctx = useContext(AppDispatchContext);
  if (ctx === null) {
    throw new Error('useAppDispatch must be used inside <AppStateProvider>');
  }
  return ctx;
}
