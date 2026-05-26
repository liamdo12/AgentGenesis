import { AgStoryCard } from '@ds/components/ag-story-card';
import { AgBulkBar } from '@ds/components/ag-bulk-bar';
import { Icon } from '@ds/lib/icons';
import { useAppDispatch, useAppState } from '../state/app-state-context';
import type { StoryFilter } from '../state/app-state-types';

const EXTRACTION_SIMULATION_MS = 1400;

const FILTERS: { id: StoryFilter; label: string }[] = [
  { id: 'all',      label: 'All' },
  { id: 'pending',  label: 'Pending' },
  { id: 'approved', label: 'Approved' },
  { id: 'high',     label: 'High priority' },
];

export function MeetingsList() {
  const { stories, filter, search, selected, approved } = useAppState();
  const dispatch = useAppDispatch();

  const filtered = stories.filter((s) => {
    if (filter === 'pending' && approved.has(s.id)) return false;
    if (filter === 'approved' && !approved.has(s.id)) return false;
    if (filter === 'high' && s.priority !== 'high') return false;
    if (search) {
      const q = search.toLowerCase();
      if (!s.title.toLowerCase().includes(q) && !s.id.toLowerCase().includes(q)) return false;
    }
    return true;
  });

  const counts: Record<StoryFilter, number> = {
    all: stories.length,
    pending: stories.filter((s) => !approved.has(s.id)).length,
    approved: stories.filter((s) => approved.has(s.id)).length,
    high: stories.filter((s) => s.priority === 'high').length,
  };

  const startExtraction = () => {
    dispatch({ type: 'START_EXTRACTION' });
    setTimeout(() => dispatch({ type: 'FINISH_EXTRACTION' }), EXTRACTION_SIMULATION_MS);
  };

  return (
    <div className="ag-stories-col">
      <div className="ag-subhead">
        <div>
          <div className="ag-subhead-title">
            Stories <span className="ag-subhead-count">{filtered.length}</span>
          </div>
          <div className="ag-subhead-meta">
            <Icon.Calendar width={11} height={11} /> From{' '}
            <strong style={{ color: 'var(--ag-text-secondary)', fontWeight: 500 }}>
              Sprint Planning · Aug 22
            </strong>{' '}
            · last extracted 8 min ago
          </div>
        </div>
        <div className="ag-subhead-actions">
          <button type="button" className="ag-btn" data-variant="ghost">
            <Icon.Sort width={12} height={12} /> Priority
          </button>
          <button type="button" className="ag-btn" onClick={startExtraction}>
            <Icon.Sparkle width={12} height={12} /> Re-extract
          </button>
          <button type="button" className="ag-btn" data-variant="primary">
            <Icon.Plus width={12} height={12} /> New story
          </button>
        </div>
      </div>

      <div className="ag-filterbar">
        <div className="ag-search">
          <span className="ag-search-icon"><Icon.Search /></span>
          <input
            placeholder="Search by title, ID, AC…"
            value={search}
            onChange={(e) => dispatch({ type: 'SET_SEARCH', payload: e.target.value })}
          />
          <span className="ag-kbd">⌘F</span>
        </div>
        {FILTERS.map((f) => (
          <button
            key={f.id}
            type="button"
            className="ag-chip"
            data-active={filter === f.id ? '' : undefined}
            onClick={() => dispatch({ type: 'SET_FILTER', payload: f.id })}
          >
            {f.label} <span className="ag-chip-count">{counts[f.id]}</span>
          </button>
        ))}
        <span style={{ marginLeft: 'auto', display: 'flex', gap: 4 }}>
          <button type="button" className="ag-iconbtn" title="List view" data-on=""><Icon.List /></button>
          <button type="button" className="ag-iconbtn" title="Board view"><Icon.Dash /></button>
        </span>
      </div>

      <div className="ag-stories">
        {filtered.length === 0 && (
          <div className="ag-empty">
            <div className="ag-empty-icon"><Icon.Search width={20} height={20} /></div>
            <div className="ag-empty-title">No stories match</div>
            <div className="ag-empty-sub">Try clearing the filter or adjust your search.</div>
            <button
              type="button"
              className="ag-btn"
              onClick={() => {
                dispatch({ type: 'SET_FILTER', payload: 'all' });
                dispatch({ type: 'SET_SEARCH', payload: '' });
              }}
            >
              Reset filters
            </button>
          </div>
        )}
        {filtered.map((s) => (
          <AgStoryCard
            key={s.id}
            story={s}
            selected={selected.has(s.id)}
            approved={approved.has(s.id)}
            onToggleSelect={() => dispatch({ type: 'TOGGLE_SELECT', payload: s.id })}
            onClick={() =>
              dispatch({ type: 'OPEN_MODAL', payload: { kind: 'edit', storyId: s.id } })
            }
          />
        ))}
      </div>

      {selected.size > 0 && (
        <AgBulkBar
          count={selected.size}
          onApprove={() => dispatch({ type: 'BULK_APPROVE' })}
          onClear={() => dispatch({ type: 'CLEAR_SELECT' })}
          onPush={() => dispatch({ type: 'OPEN_MODAL', payload: { kind: 'devops' } })}
        />
      )}
    </div>
  );
}
