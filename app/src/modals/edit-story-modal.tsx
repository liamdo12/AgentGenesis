import { Icon } from '@ds/lib/icons';
import type { Story } from '@ds/lib/seed-data';

type Props = { story: Story; onClose: () => void };

export function EditStoryModal({ story, onClose }: Props) {
  return (
    <div className="ag-modal">
      <div className="ag-modal-head">
        <span className="ag-card-id" style={{ marginTop: 0 }}>{story.id}</span>
        <span className="ag-priority" data-level={story.priority}>{story.priority}</span>
        <div className="ag-modal-title" style={{ marginLeft: 0 }}>Edit story</div>
        <div style={{ marginLeft: 'auto', display: 'flex', gap: 4 }}>
          <button type="button" className="ag-btn" data-variant="ghost">
            <Icon.Split width={12} height={12} /> Split
          </button>
          <button type="button" className="ag-iconbtn" onClick={onClose} title="Close">
            <Icon.X />
          </button>
        </div>
      </div>
      <div className="ag-modal-body">
        <div className="ag-field">
          <label>Title</label>
          <input defaultValue={story.title} />
        </div>
        <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr 1fr', gap: 10 }}>
          <div className="ag-field">
            <label>Persona</label>
            <input defaultValue={story.persona} />
          </div>
          <div className="ag-field">
            <label>I want to</label>
            <input defaultValue={story.want} />
          </div>
          <div className="ag-field">
            <label>So that</label>
            <input defaultValue={story.benefit} />
          </div>
        </div>
        <div className="ag-field">
          <label>
            Acceptance criteria{' '}
            <span style={{ color: 'var(--ag-text-faint)', fontWeight: 400, textTransform: 'none', letterSpacing: 0 }}>
              · Given / When / Then
            </span>
          </label>
          <textarea rows={4} defaultValue={story.ac} />
        </div>
        <div style={{ display: 'flex', gap: 10 }}>
          <div className="ag-field" style={{ flex: 1 }}>
            <label>Tags</label>
            <div
              style={{
                display: 'flex',
                gap: 5,
                padding: '7px 10px',
                border: '1px solid var(--ag-border)',
                borderRadius: 6,
                minHeight: 32,
                alignItems: 'center',
              }}
            >
              {story.tags.map((t) => (
                <span key={t} className="ag-tag" data-tag={t}>
                  {t} <Icon.X width={9} height={9} />
                </span>
              ))}
              <button
                type="button"
                className="ag-iconbtn"
                style={{ width: 22, height: 22, color: 'var(--ag-text-muted)' }}
              >
                <Icon.Plus width={11} height={11} />
              </button>
            </div>
          </div>
          <div className="ag-field" style={{ width: 140 }}>
            <label>Priority</label>
            <select defaultValue={story.priority}>
              <option>high</option>
              <option>med</option>
              <option>low</option>
            </select>
          </div>
          <div className="ag-field" style={{ width: 110 }}>
            <label>Estimate</label>
            <select defaultValue="5">
              <option>1</option><option>2</option><option>3</option><option>5</option><option>8</option>
            </select>
          </div>
        </div>

        <div
          style={{
            display: 'flex',
            gap: 10,
            padding: 12,
            background: 'var(--ag-msg-ai-bg)',
            border: '1px solid var(--ag-msg-ai-border)',
            borderRadius: 8,
          }}
        >
          <span
            style={{
              width: 24,
              height: 24,
              borderRadius: 7,
              background: 'linear-gradient(135deg, var(--ag-ai), var(--ag-accent))',
              color: 'white',
              display: 'flex',
              alignItems: 'center',
              justifyContent: 'center',
              flexShrink: 0,
            }}
          >
            <Icon.Sparkle width={12} height={12} />
          </span>
          <div style={{ fontSize: 12.5, color: 'var(--ag-text-secondary)', lineHeight: 1.5 }}>
            Claude suggests adding a fallback:{' '}
            <em style={{ color: 'var(--ag-text)' }}>
              "Given the transcript fails to load in 3s, then show a retry control."
            </em>
            <div style={{ display: 'flex', gap: 6, marginTop: 8 }}>
              <button type="button" className="ag-btn" style={{ height: 26, padding: '0 10px', fontSize: 12 }} data-variant="primary">
                Apply
              </button>
              <button type="button" className="ag-btn" style={{ height: 26, padding: '0 10px', fontSize: 12 }} data-variant="ghost">
                Dismiss
              </button>
            </div>
          </div>
        </div>
      </div>
      <div className="ag-modal-foot">
        <button type="button" className="ag-btn" data-variant="ghost">
          <Icon.Trash width={12} height={12} /> Delete
        </button>
        <div style={{ marginLeft: 'auto', display: 'flex', gap: 6 }}>
          <button type="button" className="ag-btn" onClick={onClose}>Cancel</button>
          <button type="button" className="ag-btn" data-variant="primary" onClick={onClose}>
            <Icon.Check width={12} height={12} /> Save &amp; approve
          </button>
        </div>
      </div>
    </div>
  );
}
