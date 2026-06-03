/**
 * Frontend story types — mirror the API `StoriesOutput` shape exactly.
 *
 * `status: 'approved' | 'pending'` is deliberately NOT on `Story` — approval
 * state lives in the `useApprovals` hook's `approved: Set<string>`, scoped
 * per run. Keeping it off the story object eliminates a dead field whose
 * value would otherwise have to be invented by the API → frontend adapter.
 */

export type Priority = 'high' | 'med' | 'low';

export type Story = {
  id: string;
  title: string;
  persona: string;
  want: string;
  benefit: string;
  ac: string;
  tags: string[];
  priority: Priority;
  meeting: string;
};

export type StoriesOutput = {
  stories: Story[];
  source_meeting_id: string;
  source_meeting_title: string;
  generated_at: string;
};

export type RunStatus =
  | 'pending'
  | 'fetching_transcript'
  | 'fetching_recording'
  | 'extracting_frames'
  | 'synthesizing'
  | 'done'
  | 'failed'
  | 'pending_transcript';

export type ApiRun = {
  id: string;
  meeting_id: string;
  user_oid: string;
  status: RunStatus;
  progress: number;
  error: string | null;
  created_at: string;
  finished_at: string | null;
  output_dir: string;
};
