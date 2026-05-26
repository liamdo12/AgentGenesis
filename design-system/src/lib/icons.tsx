import type { ReactNode, SVGProps } from 'react';

type IconProps = Omit<SVGProps<SVGSVGElement>, 'children'> & {
  width?: number | string;
  height?: number | string;
};

type IconComponent = (props?: IconProps) => JSX.Element;

const icon = (path: ReactNode, viewBox = '14'): IconComponent => {
  return ({ width = 14, height = 14, ...rest }: IconProps = {}) => (
    <svg
      width={width}
      height={height}
      viewBox={`0 0 ${viewBox} ${viewBox}`}
      fill="none"
      stroke="currentColor"
      strokeWidth="1.6"
      strokeLinecap="round"
      strokeLinejoin="round"
      aria-hidden="true"
      {...rest}
    >
      {path}
    </svg>
  );
};

export const Icon = {
  Check: icon(<path d="M3 7.2 5.8 10 11 4.2" strokeWidth="2" />),
  CheckSmall: icon(<path d="M3 7.2 5.8 10 11 4.2" strokeWidth="2.2" />),
  Plus: icon(<><path d="M7 3v8M3 7h8" /></>),
  Search: icon(<><circle cx="6" cy="6" r="3.5" /><path d="m9 9 2.5 2.5" /></>),
  ChevronDown: icon(<path d="m4 5.5 3 3 3-3" />),
  ChevronRight: icon(<path d="m5.5 4 3 3-3 3" />),
  Filter: icon(<path d="M2 3.5h10l-3.5 4v3.5L5.5 12V7.5L2 3.5z" />),
  Sort: icon(<><path d="M4 3v8M2 9l2 2 2-2" /><path d="M10 11V3M8 5l2-2 2 2" /></>),
  More: icon(
    <>
      <circle cx="3" cy="7" r="1" fill="currentColor" stroke="none" />
      <circle cx="7" cy="7" r="1" fill="currentColor" stroke="none" />
      <circle cx="11" cy="7" r="1" fill="currentColor" stroke="none" />
    </>
  ),
  X: icon(<path d="m3.5 3.5 7 7M10.5 3.5l-7 7" />),
  Sparkle: icon(
    <path
      d="M7 1.5v3M7 9.5v3M1.5 7h3M9.5 7h3M3.5 3.5 5 5M10.5 10.5 9 9M3.5 10.5 5 9M10.5 3.5 9 5"
      strokeWidth="1.4"
    />
  ),
  Calendar: icon(<><rect x="2" y="3.5" width="10" height="8.5" rx="1.5" /><path d="M2 6h10M4.5 2v3M9.5 2v3" /></>),
  List: icon(<path d="M3 4h8M3 7h8M3 10h8" />),
  Dash: icon(
    <>
      <rect x="2" y="3" width="3.5" height="3.5" rx="0.5" />
      <rect x="8.5" y="3" width="3.5" height="3.5" rx="0.5" />
      <rect x="2" y="7.5" width="3.5" height="3.5" rx="0.5" />
      <rect x="8.5" y="7.5" width="3.5" height="3.5" rx="0.5" />
    </>
  ),
  Send: icon(<path d="M2 7 12 2l-3 10-2.5-3.5L2 7z" />),
  Send2: icon(<><path d="M2.5 7h9M8 3.5 11.5 7 8 10.5" /></>),
  Mic: icon(<><rect x="5.5" y="2" width="3" height="6" rx="1.5" /><path d="M3.5 7a3.5 3.5 0 0 0 7 0M7 10.5v1.5" /></>),
  Attach: icon(<path d="M10 7.5 7 10.5a2.5 2.5 0 0 1-3.5-3.5L7.5 3a1.8 1.8 0 0 1 2.5 2.5L6.5 9" />),
  Split: icon(
    <>
      <path d="M2 11v-1.5A3.5 3.5 0 0 1 5.5 6h3A3.5 3.5 0 0 0 12 2.5V2" />
      <path d="M12 11v-1.5A3.5 3.5 0 0 0 8.5 6" />
    </>
  ),
  Edit: icon(<><path d="M2 10v2h2L11 5l-2-2-7 7z" /><path d="m8 3 2 2" /></>),
  Trash: icon(<path d="M2.5 4h9M5 4V2.5h4V4M3.5 4l.5 7.5h6l.5-7.5" />),
  Approve: icon(<><circle cx="7" cy="7" r="5" /><path d="M4.5 7 6 8.5 9.5 5" /></>),
  Push: icon(<path d="M7 11V3M3.5 6.5 7 3l3.5 3.5" />),
  Bolt: icon(<path d="M7.5 1 3 8h3l-.5 5L10 6H7l.5-5z" />),
  Hash: icon(<path d="M4 2 3 12M10 2l-1 10M2 5h10M2 9h10" strokeWidth="1.4" />),
  Loader: icon(
    <path d="M7 1v2M7 11v2M1 7h2M11 7h2M2.8 2.8l1.4 1.4M9.8 9.8l1.4 1.4M2.8 11.2l1.4-1.4M9.8 4.2l1.4-1.4" />
  ),
  ArrowUp: icon(<path d="M7 11V3M3.5 6.5 7 3l3.5 3.5" />),
  ArrowDown: icon(<path d="M7 3v8M3.5 7.5 7 11l3.5-3.5" />),
  Inbox: icon(<><path d="M2 3.5h10L11 8H9l-.5 1.5h-3L5 8H3L2 3.5z" /><path d="M2 8v3.5h10V8" /></>),
  Sun: icon(
    <>
      <circle cx="7" cy="7" r="2.5" />
      <path
        d="M7 1.5v1M7 11.5v1M12.5 7h-1M2.5 7h-1M11 3l-.7.7M3.7 10.3 3 11M11 11l-.7-.7M3.7 3.7 3 3"
        strokeWidth="1.4"
      />
    </>
  ),
  Moon: icon(<path d="M11 8.5A4.5 4.5 0 1 1 5.5 3a3.5 3.5 0 0 0 5.5 5.5z" />),
  Devops: icon(<path d="M2 5l2 2-2 2M12 5l-2 2 2 2M8 3l-2 8" strokeWidth="1.4" />),
  Star: icon(<path d="m7 1.5 1.7 3.5 3.8.5-2.8 2.7.7 3.8L7 10.2 3.6 12l.7-3.8L1.5 5.5l3.8-.5L7 1.5z" />),
  Brain: icon(
    <path
      d="M5 2.5a2 2 0 0 0-2 2v.5a1.5 1.5 0 0 0 0 3v.5a2 2 0 0 0 2 2M9 2.5a2 2 0 0 1 2 2v.5a1.5 1.5 0 0 1 0 3v.5a2 2 0 0 1-2 2M5 2.5h4M5 10.5h4M5 6.5h4"
      strokeWidth="1.4"
    />
  ),
} as const;

export type IconName = keyof typeof Icon;
