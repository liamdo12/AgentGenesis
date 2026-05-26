import type { MouseEvent } from 'react';
import { Icon } from '../lib/icons';
import type { Story } from '../lib/seed-data';

export type CardStyle = 'bordered' | 'flat' | 'hairline';

type StoryCardProps = {
  story: Story;
  selected?: boolean;
  approved?: boolean;
  cardStyle?: CardStyle;
  onToggleSelect?: () => void;
  onClick?: () => void;
};

export function AgStoryCard({
  story,
  selected,
  approved,
  cardStyle,
  onToggleSelect,
  onClick,
}: StoryCardProps) {
  const stop = (e: MouseEvent) => {
    e.stopPropagation();
    onToggleSelect?.();
  };
  return (
    <div
      className="ag-card"
      {...(selected ? { 'data-selected': '' } : {})}
      {...(approved ? { 'data-approved': '' } : {})}
      {...(cardStyle ? { 'data-style': cardStyle } : {})}
      onClick={onClick}
    >
      <div className="ag-card-head">
        <button
          type="button"
          className="ag-card-check"
          {...(selected ? { 'data-checked': '' } : {})}
          onClick={stop}
          title={selected ? 'Deselect' : 'Select'}
        >
          {selected && <Icon.CheckSmall width={11} height={11} />}
        </button>
        <div style={{ flex: 1, display: 'flex', flexDirection: 'column', gap: 2 }}>
          <div className="ag-card-id">{story.id}</div>
          <div className="ag-card-title">{story.title}</div>
        </div>
        <span className="ag-priority" data-level={story.priority}>
          {story.priority}
        </span>
      </div>
      <div className="ag-card-body">
        As a <em>{story.persona}</em>, I want to <em>{story.want}</em> so that <em>{story.benefit}</em>.
      </div>
      <div className="ag-card-ac">
        <span className="ag-card-ac-label">AC</span>
        <span>{story.ac}</span>
      </div>
      <div className="ag-card-foot">
        {story.tags.map((t) => (
          <span key={t} className="ag-tag" data-tag={t}>
            {t}
          </span>
        ))}
        <span className="ag-card-source">
          <Icon.Calendar width={11} height={11} /> {story.meeting}
        </span>
        <div className="ag-card-action">
          {approved ? (
            <span
              className="ag-tag"
              style={{ background: 'var(--ag-success-soft)', color: 'var(--ag-success)' }}
            >
              <Icon.Check width={10} height={10} /> Approved
            </span>
          ) : (
            <button
              type="button"
              className="ag-btn"
              style={{ height: 24, padding: '0 8px', fontSize: 11.5 }}
              onClick={stop}
            >
              <Icon.Check width={11} height={11} /> Approve
            </button>
          )}
          <button
            type="button"
            className="ag-iconbtn"
            style={{ width: 24, height: 24 }}
            title="More"
            onClick={(e) => e.stopPropagation()}
          >
            <Icon.More width={12} height={12} />
          </button>
        </div>
      </div>
    </div>
  );
}
