import { Icon } from '@ds/lib/icons';
import { MeetingDropdown } from '../components/meeting-dropdown';
import { useMeetings } from '../hooks/use-meetings';
import { useAppDispatch, useAppState } from '../state/app-state-context';

const EXTRACTION_SIMULATION_MS = 1400;

export function MeetingsEmpty() {
  const { selectedMeetingId } = useAppState();
  // Live meetings from /meetings — replaces seed data. Per red-team Finding 12,
  // fetch is hoisted here (panel level), not pushed into MeetingDropdown.
  const { meetings, loading, error } = useMeetings();
  const dispatch = useAppDispatch();

  // Picking a meeting both records the selection and kicks off extraction.
  // Matches the meetings-list "Re-extract" simulation timing.
  const pickAndExtract = (id: string) => {
    dispatch({ type: 'SET_SELECTED_MEETING', payload: id });
    dispatch({ type: 'START_EXTRACTION' });
    setTimeout(() => dispatch({ type: 'FINISH_EXTRACTION' }), EXTRACTION_SIMULATION_MS);
  };

  return (
    <div className="ag-stories-col">
      <div className="ag-subhead">
        <div>
          <div className="ag-subhead-title">
            Stories <span className="ag-subhead-count">0</span>
          </div>
          <div className="ag-subhead-meta">No stories extracted yet</div>
        </div>
        <div className="ag-subhead-actions">
          <button type="button" className="ag-btn" data-variant="primary">
            <Icon.Plus width={12} height={12} /> New story
          </button>
        </div>
      </div>

      <div className="ag-empty" style={{ paddingTop: 60 }}>
        <div className="ag-empty-icon" style={{ width: 64, height: 64, borderRadius: 16 }}>
          <Icon.Calendar width={24} height={24} />
        </div>
        <div className="ag-empty-title">No stories yet</div>
        <div className="ag-empty-sub">
          Connect a meeting recording, paste a transcript, or invite Genesis Bot to your next call.
          Stories will appear here.
        </div>
        <div style={{ display: 'flex', gap: 8, alignItems: 'center', flexDirection: 'column' }}>
          <div style={{ display: 'flex', gap: 8, alignItems: 'center' }}>
            <MeetingDropdown
              meetings={meetings}
              selectedId={selectedMeetingId}
              onSelect={pickAndExtract}
              placeholder={loading ? 'Loading meetings…' : 'Select a meeting'}
              size="lg"
            />
            <button type="button" className="ag-btn" data-size="lg">
              <Icon.Plus width={13} height={13} /> Paste transcript
            </button>
          </div>
          {error && (
            <div style={{ fontSize: 12, color: 'var(--ag-danger)' }}>
              Failed to load meetings: {error}
            </div>
          )}
        </div>
      </div>
    </div>
  );
}
