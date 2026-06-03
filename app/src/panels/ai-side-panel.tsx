import {
  AgAIHeader,
  AgComposer,
  AgContextStrip,
  AgMessage,
  AgQuickBar,
} from '@ds/components/ag-ai-panel';
import { Icon } from '@ds/lib/icons';
import { useChat } from '../hooks/use-chat';
import { BulkDeletePreviewModal } from '../modals/bulk-delete-preview-modal';
import { useAppState } from '../state/app-state-context';
import type { Story } from '../lib/story-types';

type Props = {
  onRevision?: (stories: Story[]) => void;
};

export function AiSidePanel({ onRevision }: Props = {}) {
  const { stories, activeRunId, selectedMeetingId } = useAppState();
  const chat = useChat(activeRunId, onRevision);

  if (stories.length === 0) {
    return <EmptyAiBody />;
  }

  const meetingLabel = selectedMeetingId ?? 'Active meeting';

  return (
    <div className="ag-ai-col">
      <AgAIHeader />
      <AgContextStrip meeting={meetingLabel} count={stories.length} />
      {chat.error && (
        <div style={{ padding: '6px 12px', color: 'var(--ag-danger)', fontSize: 12 }}>
          {chat.error}
          {' · '}
          <button
            type="button"
            onClick={chat.clearHistory}
            style={{ background: 'none', border: 'none', color: 'inherit', textDecoration: 'underline', cursor: 'pointer' }}
          >
            Clear history
          </button>
        </div>
      )}
      <div className="ag-ai-messages">
        {chat.messages.map((m) => (
          <AgMessage
            key={m.id}
            from={m.role === 'user' ? 'user' : 'ai'}
            body={
              <div>
                {m.status === 'error' ? (
                  <p style={{ color: 'var(--ag-danger)' }}>
                    {m.content || 'Claude was interrupted.'} ({m.errorDetail ?? 'error'})
                  </p>
                ) : (
                  <p style={{ whiteSpace: 'pre-wrap' }}>{m.content}</p>
                )}
                {m.revisionVersion != null && m.role === 'assistant' && (
                  <RestoreLink
                    version={m.revisionVersion - 1}
                    onRestore={chat.restore}
                  />
                )}
              </div>
            }
          />
        ))}
        {chat.streaming && <AgMessage from="ai" typing />}
      </div>
      <AgQuickBar onPick={chat.send} />
      <AgComposer onSend={chat.send} />
      {chat.streaming && (
        <div style={{ padding: '4px 12px', textAlign: 'right' }}>
          <button
            type="button"
            className="ag-btn"
            data-variant="ghost"
            onClick={chat.cancel}
            title="Stop generation"
          >
            Stop
          </button>
        </div>
      )}
      {chat.preview && (
        <BulkDeletePreviewModal
          preview={chat.preview}
          onAccept={() => chat.acceptPreview(chat.preview!.previewId)}
          onReject={chat.rejectPreview}
        />
      )}
    </div>
  );
}

function RestoreLink({ version, onRestore }: { version: number; onRestore: (v: number) => void }) {
  if (version < 1) return null;
  return (
    <button
      type="button"
      onClick={() => onRestore(version)}
      style={{
        marginTop: 6,
        background: 'none',
        border: 'none',
        color: 'var(--ag-ai)',
        textDecoration: 'underline',
        cursor: 'pointer',
        fontSize: 12,
      }}
    >
      Undo to revision {version}
    </button>
  );
}

function EmptyAiBody() {
  return (
    <div className="ag-ai-col">
      <AgAIHeader />
      <div
        style={{
          padding: 16,
          flex: 1,
          display: 'flex',
          flexDirection: 'column',
          gap: 12,
          justifyContent: 'center',
          alignItems: 'center',
          textAlign: 'center',
        }}
      >
        <span
          style={{
            width: 40,
            height: 40,
            borderRadius: 11,
            background: 'linear-gradient(135deg, var(--ag-ai) 0%, var(--ag-accent) 100%)',
            color: 'white',
            display: 'flex',
            alignItems: 'center',
            justifyContent: 'center',
            boxShadow: '0 6px 20px -4px rgba(124, 92, 255, 0.4)',
          }}
        >
          <Icon.Sparkle width={18} height={18} />
        </span>
        <div style={{ fontSize: 14, fontWeight: 600, letterSpacing: '-0.01em' }}>
          Pick a meeting to get started
        </div>
        <div style={{ fontSize: 12.5, color: 'var(--ag-text-muted)', maxWidth: 220, lineHeight: 1.5 }}>
          Connect a meeting transcript and I'll extract user stories with acceptance criteria.
        </div>
        <button type="button" className="ag-btn" data-variant="primary" style={{ marginTop: 4 }}>
          <Icon.Calendar width={12} height={12} /> Connect a meeting
        </button>
      </div>
    </div>
  );
}
