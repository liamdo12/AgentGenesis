import { AG_MEETINGS, AG_MESSAGES, AG_STORIES } from '@ds/lib/seed-data';
import { DEFAULT_TWEAKS } from '../lib/use-tweaks';
import type { Action, AppState } from './app-state-types';

export function initialState(): AppState {
  return {
    topTab: 'Stories',
    stories: AG_STORIES,
    selected: new Set(),
    approved: new Set(['AG-024']),
    focused: null,
    filter: 'all',
    search: '',
    phase: 'idle',
    modal: null,
    messages: AG_MESSAGES,
    composer: '',
    aiThinking: false,
    tweaks: DEFAULT_TWEAKS,
    meetings: AG_MEETINGS,
    // Seeded to the first meeting so the list view's "From <meeting>" subhead
    // has a value to display without the user picking one first.
    selectedMeetingId: AG_MEETINGS[0]?.id ?? null,
  };
}

export function reducer(state: AppState, action: Action): AppState {
  switch (action.type) {
    case 'SET_TOP_TAB':
      return { ...state, topTab: action.payload };

    case 'SET_FILTER':
      return { ...state, filter: action.payload };

    case 'SET_SEARCH':
      return { ...state, search: action.payload };

    case 'TOGGLE_SELECT': {
      const next = new Set(state.selected);
      if (next.has(action.payload)) next.delete(action.payload);
      else next.add(action.payload);
      return { ...state, selected: next };
    }

    case 'CLEAR_SELECT':
      return { ...state, selected: new Set() };

    case 'BULK_APPROVE': {
      const next = new Set(state.approved);
      state.selected.forEach((id) => next.add(id));
      return { ...state, approved: next, selected: new Set() };
    }

    case 'APPROVE': {
      const next = new Set(state.approved);
      action.payload.forEach((id) => next.add(id));
      return { ...state, approved: next };
    }

    case 'APPROVE_ALL': {
      // Union with prior so previously-approved ids that no longer appear in
      // state.stories (e.g. after a future filter/refetch) are not silently dropped.
      const next = new Set(state.approved);
      state.stories.forEach((s) => next.add(s.id));
      return { ...state, approved: next };
    }

    case 'SET_FOCUSED':
      return { ...state, focused: action.payload };

    case 'OPEN_MODAL': {
      if (action.payload.kind === 'edit') {
        const { storyId } = action.payload;
        const exists = state.stories.some((s) => s.id === storyId);
        if (!exists) return { ...state, modal: null };
      }
      return { ...state, modal: action.payload };
    }

    case 'CLOSE_MODAL':
      return { ...state, modal: null };

    case 'SET_SELECTED_MEETING':
      return { ...state, selectedMeetingId: action.payload };

    case 'START_EXTRACTION':
      return { ...state, phase: 'extracting' };

    case 'FINISH_EXTRACTION':
      return { ...state, phase: 'idle' };

    case 'SEND_USER_MESSAGE':
      return { ...state, messages: [...state.messages, action.payload], composer: '' };

    case 'AI_REPLY':
      return { ...state, messages: [...state.messages, action.payload], aiThinking: false };

    case 'AI_THINKING':
      return { ...state, aiThinking: action.payload };

    case 'SET_COMPOSER':
      return { ...state, composer: action.payload };

    case 'SET_TWEAK':
      return {
        ...state,
        tweaks: { ...state.tweaks, [action.payload.key]: action.payload.value },
      };

    default: {
      // Exhaustiveness guard: compile error if a new Action variant is added
      // without a matching case here.
      const _exhaustive: never = action;
      void _exhaustive;
      return state;
    }
  }
}
