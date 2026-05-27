import type { ReactNode } from 'react';
import { Icon, type IconName } from './icons';

export type Priority = 'high' | 'med' | 'low';
export type Status = 'approved' | 'pending';

export type Meeting = {
  id: string;
  title: string;
  // Human-readable date + duration, e.g. "Aug 22 · 42 min". Pre-formatted to
  // avoid a runtime date library purely for cosmetic copy.
  detail: string;
  candidates: number;
};

// Source of truth for the meeting picker. The first entry is the default
// selection on first load; story seed data currently quotes its label.
export const AG_MEETINGS: Meeting[] = [
  { id: 'm-sprint-22',    title: 'Sprint Planning',            detail: 'Aug 22 · 42 min', candidates: 5 },
  { id: 'm-discovery-21', title: 'Customer Discovery — Acme',  detail: 'Aug 21 · 28 min', candidates: 5 },
  { id: 'm-retro-20',     title: 'Retro · Sprint 14',          detail: 'Aug 20 · 35 min', candidates: 2 },
  { id: 'm-design-19',    title: 'Design Review · Onboarding', detail: 'Aug 19 · 51 min', candidates: 4 },
  { id: 'm-standup-18',   title: 'Engineering Sync',           detail: 'Aug 18 · 22 min', candidates: 1 },
];

export type Story = {
  id: string;
  title: string;
  persona: string;
  want: string;
  benefit: string;
  ac: string;
  tags: string[];
  priority: Priority;
  status: Status;
  meeting: string;
};

export const AG_STORIES: Story[] = [
  {
    id: 'AG-024',
    title: 'User authentication with SSO',
    persona: 'corporate user',
    want: 'log in using my company SSO',
    benefit: "I don't manage separate credentials",
    ac: 'Given SSO is configured, when I visit the URL, then I see the Azure AD login prompt.',
    tags: ['Auth'],
    priority: 'high',
    status: 'approved',
    meeting: 'Sprint Planning · Aug 22',
  },
  {
    id: 'AG-025',
    title: 'Meeting transcript auto-fetch',
    persona: 'product manager',
    want: 'transcripts to load automatically after I log in',
    benefit: 'I can start extracting stories immediately',
    ac: "Given I'm authenticated, when I select a meeting, then the transcript loads within 3 seconds.",
    tags: ['Meetings'],
    priority: 'high',
    status: 'pending',
    meeting: 'Sprint Planning · Aug 22',
  },
  {
    id: 'AG-026',
    title: 'Bulk story export to DevOps',
    persona: 'BA',
    want: 'push all approved stories to Azure DevOps in one click',
    benefit: 'I save manual data entry time',
    ac: 'Given at least one story is approved, when I click Push, then PBIs are created in the configured project.',
    tags: ['DevOps'],
    priority: 'med',
    status: 'pending',
    meeting: 'Sprint Planning · Aug 22',
  },
  {
    id: 'AG-027',
    title: 'Acceptance criteria refinement loop',
    persona: 'developer',
    want: 'ask Claude to rewrite vague AC into Given/When/Then',
    benefit: 'I can pick the story up without follow-up questions',
    ac: 'Given a story has fewer than 3 AC, when I click Refine, then Claude proposes 3+ AC in GWT format.',
    tags: ['AI'],
    priority: 'med',
    status: 'pending',
    meeting: 'Sprint Planning · Aug 22',
  },
  {
    id: 'AG-028',
    title: 'Story estimation hints',
    persona: 'scrum master',
    want: 'see suggested story points based on similar past stories',
    benefit: 'planning poker runs faster and more consistently',
    ac: 'Given a story is approved, when I open it, then I see a suggested estimate with 3 nearest neighbours.',
    tags: ['Meetings'],
    priority: 'low',
    status: 'pending',
    meeting: 'Sprint Planning · Aug 22',
  },
];

export type Message = {
  from: 'ai' | 'user';
  body?: ReactNode;
  card?: { txt: string; ok?: boolean }[];
  time?: string;
  typing?: boolean;
};

export const AG_MESSAGES: Message[] = [
  {
    from: 'ai',
    body: (
      <p>
        Hi! I'm your Agent Genesis assistant. Extract stories from a meeting, then ask me to approve,
        prioritise, or split them.
      </p>
    ),
    time: '10:42',
  },
  {
    from: 'ai',
    body: (
      <p>
        Found <strong>3 user stories</strong> in <em>Sprint Planning · Aug 22</em>. Review and click{' '}
        <Icon.Check width="11" height="11" style={{ display: 'inline', verticalAlign: '-2px' }} /> to
        approve, or ask me to approve all.
      </p>
    ),
    card: [
      { txt: 'AG-024 · User authentication with SSO', ok: true },
      { txt: 'AG-025 · Meeting transcript auto-fetch', ok: true },
      { txt: 'AG-026 · Bulk story export to DevOps', ok: true },
    ],
    time: '10:42',
  },
];

export type QuickAction = { label: string; icon: IconName };

export const AG_QUICK: QuickAction[] = [
  { label: 'Approve all', icon: 'Check' },
  { label: 'Raise priorities', icon: 'ArrowUp' },
  { label: 'Summarise', icon: 'List' },
  { label: 'Split AG-026', icon: 'Split' },
];

export const ICON_SET: IconName[] = [
  'Check', 'Plus', 'Search', 'ChevronDown', 'ChevronRight', 'Filter', 'Sort',
  'More', 'X', 'Sparkle', 'Calendar', 'List', 'Dash', 'Send2', 'Mic', 'Attach',
  'Split', 'Edit', 'Trash', 'Approve', 'Push', 'Bolt', 'Hash', 'ArrowUp',
  'ArrowDown', 'Inbox', 'Sun', 'Moon', 'Star',
];

