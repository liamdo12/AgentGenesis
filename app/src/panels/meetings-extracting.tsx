import { AgStoryCard } from '@ds/components/ag-story-card';
import { Icon } from '@ds/lib/icons';
import { useAppDispatch, useAppState } from '../state/app-state-context';

const Skel = ({ w, h = 11 }: { w: number | string; h?: number }) => (
  <div className="ag-shimmer" style={{ height: h, width: w }} />
);

const SKELETON_ROWS = [0, 1, 2];

export function MeetingsExtracting() {
  const { stories, approved } = useAppState();
  const dispatch = useAppDispatch();
  const realCards = stories.slice(0, 2);
  return (
    <div className="ag-stories-col">
      <div className="ag-subhead">
        <div>
          <div className="ag-subhead-title">
            Stories{' '}
            <span
              className="ag-subhead-count"
              style={{ background: 'var(--ag-accent-soft)', color: 'var(--ag-accent-text)' }}
            >
              extracting…
            </span>
          </div>
          <div className="ag-subhead-meta">
            <span style={{ display: 'inline-flex', alignItems: 'center', gap: 6 }}>
              <span
                style={{
                  width: 12,
                  height: 12,
                  borderRadius: '50%',
                  background:
                    'conic-gradient(var(--ag-accent) 0% 40%, var(--ag-surface-2) 40% 100%)',
                  animation: 'ag-spin 1.4s linear infinite',
                }}
              />
              <span>Reading transcript · 40%</span>
            </span>
          </div>
        </div>
        <div className="ag-subhead-actions">
          <button
            type="button"
            className="ag-btn"
            data-variant="ghost"
            onClick={() => dispatch({ type: 'FINISH_EXTRACTION' })}
          >
            <Icon.X width={12} height={12} /> Cancel
          </button>
        </div>
      </div>

      <style>{`@keyframes ag-spin { to { transform: rotate(360deg); } }`}</style>

      <div className="ag-stories">
        {realCards.map((s) => (
          <AgStoryCard key={s.id} story={s} approved={approved.has(s.id)} />
        ))}

        {SKELETON_ROWS.map((i) => (
          <div key={i} className="ag-card" style={{ pointerEvents: 'none' }}>
            <div className="ag-card-head">
              <div className="ag-card-check" />
              <div style={{ flex: 1, display: 'flex', flexDirection: 'column', gap: 6 }}>
                <Skel w={42} h={10} />
                <Skel w={`${65 - i * 8}%`} h={14} />
              </div>
              <Skel w={40} h={18} />
            </div>
            <div style={{ paddingLeft: 26, display: 'flex', flexDirection: 'column', gap: 6 }}>
              <Skel w="92%" />
              <Skel w="70%" />
            </div>
            <div style={{ paddingLeft: 26 }}>
              <Skel w="60%" />
            </div>
            <div style={{ paddingLeft: 26, display: 'flex', gap: 8 }}>
              <Skel w={40} h={16} />
              <Skel w={120} h={12} />
            </div>
          </div>
        ))}
      </div>
    </div>
  );
}
