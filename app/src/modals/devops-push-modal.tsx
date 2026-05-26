import { Icon } from '@ds/lib/icons';
import { useAppState } from '../state/app-state-context';

type Props = { onClose: () => void };

export function DevOpsPushModal({ onClose }: Props) {
  const { stories, approved } = useAppState();
  const toPush = stories.filter((s) => approved.has(s.id));
  const count = toPush.length;

  return (
    <div className="ag-modal" style={{ width: 'min(520px, calc(100% - 48px))' }}>
      <div className="ag-modal-head">
        <span
          style={{
            width: 32,
            height: 32,
            borderRadius: 8,
            background: '#0078d4',
            color: 'white',
            display: 'flex',
            alignItems: 'center',
            justifyContent: 'center',
          }}
        >
          <Icon.Push width={16} height={16} />
        </span>
        <div>
          <div className="ag-modal-title">Push to Azure DevOps</div>
          <div style={{ fontSize: 12, color: 'var(--ag-text-muted)', marginTop: 2 }}>
            {count} approved {count === 1 ? 'story' : 'stories'} →{' '}
            <strong style={{ color: 'var(--ag-text-secondary)' }}>genesis/Sprint-15</strong>
          </div>
        </div>
        <button type="button" className="ag-iconbtn" style={{ marginLeft: 'auto' }} onClick={onClose} title="Close">
          <Icon.X />
        </button>
      </div>
      <div className="ag-modal-body">
        <div style={{ display: 'flex', flexDirection: 'column', gap: 6 }}>
          {toPush.map((s) => (
            <div
              key={s.id}
              style={{
                display: 'flex',
                alignItems: 'center',
                gap: 10,
                padding: '8px 10px',
                border: '1px solid var(--ag-border)',
                borderRadius: 7,
                background: 'var(--ag-surface)',
              }}
            >
              <span
                style={{
                  width: 18,
                  height: 18,
                  borderRadius: 4,
                  background: 'var(--ag-success-soft)',
                  color: 'var(--ag-success)',
                  display: 'flex',
                  alignItems: 'center',
                  justifyContent: 'center',
                }}
              >
                <Icon.Check width={11} height={11} />
              </span>
              <span className="ag-card-id" style={{ marginTop: 0 }}>{s.id}</span>
              <span style={{ fontSize: 13, fontWeight: 500, flex: 1 }}>{s.title}</span>
              <span
                className="ag-priority"
                data-level={s.priority}
                style={{ fontSize: 9.5, padding: '1px 6px' }}
              >
                {s.priority}
              </span>
              <span style={{ fontSize: 12, color: 'var(--ag-text-muted)' }}>→ PBI</span>
            </div>
          ))}
        </div>

        <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 10 }}>
          <div className="ag-field">
            <label>Project</label>
            <select defaultValue="Genesis">
              <option>Genesis</option>
              <option>Atlas</option>
            </select>
          </div>
          <div className="ag-field">
            <label>Iteration</label>
            <select defaultValue="Sprint 15">
              <option>Sprint 15</option>
              <option>Sprint 16</option>
            </select>
          </div>
        </div>

        <label
          style={{
            display: 'flex',
            alignItems: 'center',
            gap: 8,
            fontSize: 12.5,
            color: 'var(--ag-text-secondary)',
          }}
        >
          <span
            className="ag-card-check"
            data-checked=""
            style={{ background: 'var(--ag-accent)', borderColor: 'var(--ag-accent)', color: 'white' }}
          >
            <Icon.CheckSmall width={11} height={11} />
          </span>
          Include acceptance criteria in description
        </label>
      </div>
      <div className="ag-modal-foot">
        <span style={{ fontSize: 12, color: 'var(--ag-text-muted)' }}>
          {count} {count === 1 ? 'PBI' : 'PBIs'} will be created.
        </span>
        <div style={{ marginLeft: 'auto', display: 'flex', gap: 6 }}>
          <button type="button" className="ag-btn" onClick={onClose}>Cancel</button>
          <button type="button" className="ag-btn" data-variant="primary" onClick={onClose}>
            <Icon.Push width={12} height={12} /> Push {count} {count === 1 ? 'story' : 'stories'}
          </button>
        </div>
      </div>
    </div>
  );
}
