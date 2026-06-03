import type { Meeting, Message } from '@ds/lib/seed-data';
import type { ApiRun, RunStatus, Story } from '../lib/story-types';
import type { Tweaks } from '../lib/use-tweaks';

export type TopTab = 'Meetings' | 'Stories' | 'Dashboard';
export type StoryFilter = 'all' | 'pending' | 'approved' | 'high';
export type ExtractionPhase = 'idle' | 'extracting';

export type ModalState =
  | null
  | { kind: 'edit'; storyId: string }
  | { kind: 'devops' };

export type AppState = {
  topTab: TopTab;
  stories: Story[];
  selected: Set<string>;
  approved: Set<string>;
  focused: string | null;
  filter: StoryFilter;
  search: string;
  phase: ExtractionPhase;
  modal: ModalState;
  messages: Message[];
  composer: string;
  aiThinking: boolean;
  tweaks: Tweaks;
  meetings: Meeting[];
  // `null` only briefly on cold start before the dropdown defaults to the
  // first meeting; UI treats null as "no meeting selected" (empty state).
  selectedMeetingId: string | null;
  // Live run state — populated by the run-lifecycle hooks.
  activeRunId: string | null;
  runStatus: RunStatus | null;
  runError: string | null;
};

export type Action =
  | { type: 'SET_TOP_TAB'; payload: TopTab }
  | { type: 'SET_FILTER'; payload: StoryFilter }
  | { type: 'SET_SEARCH'; payload: string }
  | { type: 'TOGGLE_SELECT'; payload: string }
  | { type: 'CLEAR_SELECT' }
  | { type: 'BULK_APPROVE' }
  | { type: 'APPROVE'; payload: string[] }
  | { type: 'APPROVE_ALL' }
  | { type: 'SET_FOCUSED'; payload: string | null }
  | { type: 'OPEN_MODAL'; payload: NonNullable<ModalState> }
  | { type: 'CLOSE_MODAL' }
  | { type: 'SET_SELECTED_MEETING'; payload: string }
  | { type: 'START_EXTRACTION' }
  | { type: 'FINISH_EXTRACTION' }
  | { type: 'SET_ACTIVE_RUN'; payload: string | null }
  | { type: 'SET_STORIES_FROM_SERVER'; payload: Story[] }
  | { type: 'RUN_PROGRESS'; payload: ApiRun }
  | { type: 'RUN_DONE'; payload: ApiRun }
  | { type: 'RUN_FAILED'; payload: { error: string } }
  | { type: 'SEND_USER_MESSAGE'; payload: Message }
  | { type: 'AI_REPLY'; payload: Message }
  | { type: 'AI_THINKING'; payload: boolean }
  | { type: 'SET_COMPOSER'; payload: string }
  | { type: 'SET_TWEAK'; payload: { [K in keyof Tweaks]: { key: K; value: Tweaks[K] } }[keyof Tweaks] };
