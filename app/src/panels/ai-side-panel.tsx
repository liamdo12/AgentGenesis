import {
  AgAIHeader,
  AgComposer,
  AgContextStrip,
  AgMessage,
  AgQuickBar,
} from '@ds/components/ag-ai-panel';
import { Icon } from '@ds/lib/icons';
import { useAppDispatch, useAppState } from '../state/app-state-context';
import type { Message } from '@ds/lib/seed-data';

export function AiSidePanel() {
  const { stories, messages, composer, aiThinking, phase } = useAppState();
  const dispatch = useAppDispatch();

  if (stories.length === 0) {
    return <EmptyAiBody />;
  }

  const sendMessage = (txt: string) => {
    dispatch({
      type: 'SEND_USER_MESSAGE',
      payload: { from: 'user', body: <p>{txt}</p>, time: 'now' },
    });
    dispatch({ type: 'AI_THINKING', payload: true });
    setTimeout(() => dispatch({ type: 'AI_REPLY', payload: aiReply(txt) }), 850);
  };

  const extractionMessages: Message[] =
    phase === 'extracting'
      ? [
          { from: 'ai', typing: true },
          {
            from: 'ai',
            body: (
              <p>
                Working through <em>Sprint Planning · Aug 22</em> — extracted{' '}
                <strong>2 of ~5</strong> candidates so far.
              </p>
            ),
          },
        ]
      : [];

  return (
    <div className="ag-ai-col">
      <AgAIHeader />
      <AgContextStrip meeting="Sprint Planning · Aug 22" count={stories.length} />
      <div className="ag-ai-messages">
        {messages.map((m, i) => <AgMessage key={i} {...m} />)}
        {extractionMessages.map((m, i) => <AgMessage key={`x${i}`} {...m} />)}
        {aiThinking && phase !== 'extracting' && <AgMessage from="ai" typing />}
      </div>
      <AgQuickBar onPick={sendMessage} />
      <AgComposer
        value={composer}
        onChange={(v) => dispatch({ type: 'SET_COMPOSER', payload: v })}
        onSend={sendMessage}
      />
    </div>
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

function aiReply(txt: string): Message {
  if (/approve all/i.test(txt)) {
    return {
      from: 'ai',
      body: <p>Approved all stories. Push to DevOps when ready.</p>,
      time: 'now',
    };
  }
  if (/priorit/i.test(txt)) {
    return {
      from: 'ai',
      body: (
        <p>
          Bumped <strong>AG-025</strong> and <strong>AG-026</strong> to <em>high</em>.
        </p>
      ),
      time: 'now',
    };
  }
  if (/split/i.test(txt)) {
    return {
      from: 'ai',
      body: <p>I'd split <strong>AG-026</strong> into UI + API tickets.</p>,
      time: 'now',
    };
  }
  if (/summar/i.test(txt)) {
    return {
      from: 'ai',
      body: <p>3 stories: login → ingestion → push. ~4–6 points each.</p>,
      time: 'now',
    };
  }
  return { from: 'ai', body: <p>Done. Anything else?</p>, time: 'now' };
}
