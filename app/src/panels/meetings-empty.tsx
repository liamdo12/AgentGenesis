import { Icon } from '@ds/lib/icons';
import { MeetingDropdown } from '../components/meeting-dropdown';
import { useMeetings } from '../hooks/use-meetings';
import { useAppDispatch, useAppState } from '../state/app-state-context';

type Props = {
  onStartExtraction?: () => Promise<string | null>;
  loading?: boolean;
  error?: string | null;
};

export function MeetingsEmpty({ onStartExtraction, loading, error: lifecycleError }: Props = {}) {
  const { selectedMeetingId } = useAppState();
  const { meetings, loading: meetingsLoading, error: meetingsError } = useMeetings();
  const dispatch = useAppDispatch();

  const pickMeeting = (id: string) => {
    dispatch({ type: 'SET_SELECTED_MEETING', payload: id });
  };

  const handleStart = async () => {
    if (!onStartExtraction) return;
    dispatch({ type: 'START_EXTRACTION' });
    await onStartExtraction();
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
          Pick a meeting recording and click <strong>Start extraction</strong>.
          Stories will appear here once Claude finishes.
        </div>
        <div style={{ display: 'flex', gap: 8, alignItems: 'center', flexDirection: 'column' }}>
          <div style={{ display: 'flex', gap: 8, alignItems: 'center' }}>
            <MeetingDropdown
              meetings={meetings}
              selectedId={selectedMeetingId}
              onSelect={pickMeeting}
              placeholder={meetingsLoading ? 'Loading meetings…' : 'Select a meeting'}
              size="lg"
            />
            <button
              type="button"
              className="ag-btn"
              data-size="lg"
              data-variant="primary"
              disabled={!selectedMeetingId || loading}
              onClick={handleStart}
            >
              <Icon.Sparkle width={13} height={13} /> Start extraction
            </button>
          </div>
          {(meetingsError || lifecycleError) && (
            <div style={{ fontSize: 12, color: 'var(--ag-danger)' }}>
              {meetingsError ?? lifecycleError}
            </div>
          )}
        </div>
      </div>
    </div>
  );
}
