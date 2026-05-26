import { useEffect, useRef, type CSSProperties, type ReactNode } from 'react';
import { Icon } from '../lib/icons';
import { AG_QUICK, type QuickAction } from '../lib/seed-data';

export function AgAIHeader() {
  return (
    <div className="ag-ai-head">
      <span className="ag-ai-icon">
        <Icon.Sparkle width={13} height={13} />
      </span>
      <div style={{ flex: 1, minWidth: 0 }}>
        <div className="ag-ai-title">Assistant</div>
        <div className="ag-ai-sub">Claude · ready · 4 actions available</div>
      </div>
      <button type="button" className="ag-iconbtn" title="Clear thread">
        <Icon.Trash width={12} height={12} />
      </button>
      <button type="button" className="ag-iconbtn" title="Settings">
        <Icon.More width={12} height={12} />
      </button>
    </div>
  );
}

type ContextStripProps = { meeting?: string; count?: number };

export function AgContextStrip({
  meeting = 'Sprint Planning · Aug 22',
  count = 3,
}: ContextStripProps) {
  return (
    <div className="ag-ai-context">
      <span className="ag-ai-context-lbl">Context</span>
      <span>
        <strong>{meeting}</strong>
      </span>
      <span style={{ marginLeft: 'auto', color: 'var(--ag-text-muted)' }}>{count} stories</span>
    </div>
  );
}

const dot = (delay: number): CSSProperties => ({
  width: 5,
  height: 5,
  borderRadius: '50%',
  background: 'var(--ag-text-muted)',
  animation: 'ag-dot 1.1s ease-in-out infinite',
  animationDelay: `${delay}s`,
});

export function AgTypingDots() {
  return (
    <span style={{ display: 'inline-flex', gap: 4, padding: '6px 2px' }}>
      <i style={dot(0)} />
      <i style={dot(0.15)} />
      <i style={dot(0.3)} />
      <style>{`@keyframes ag-dot { 0%, 60%, 100% { transform: translateY(0); opacity: 0.4; } 30% { transform: translateY(-3px); opacity: 1; } }`}</style>
    </span>
  );
}

type MessageProps = {
  from: 'ai' | 'user';
  body?: ReactNode;
  card?: { txt: string; ok?: boolean }[];
  time?: string;
  typing?: boolean;
};

export function AgMessage({ from, body, card, time, typing }: MessageProps) {
  return (
    <div className="ag-msg">
      <span className="ag-msg-avatar" data-from={from}>
        {from === 'ai' ? <Icon.Sparkle width={11} height={11} /> : 'R'}
      </span>
      <div className="ag-msg-body">
        {typing ? <AgTypingDots /> : body}
        {card && (
          <div className="ag-msg-card">
            {card.map((r, i) => (
              <div key={i} className="ag-msg-card-row">
                {r.ok && <Icon.Check width={11} height={11} />}
                <span>{r.txt}</span>
              </div>
            ))}
          </div>
        )}
        {time && <div className="ag-msg-meta">{time}</div>}
      </div>
    </div>
  );
}

type QuickBarProps = { items?: QuickAction[]; onPick?: (label: string) => void };

export function AgQuickBar({ items = AG_QUICK, onPick }: QuickBarProps) {
  return (
    <div className="ag-quickbar">
      <div className="ag-quickbar-label">Suggested</div>
      {items.map((q) => {
        const Ic = Icon[q.icon] ?? Icon.Sparkle;
        return (
          <button type="button" key={q.label} className="ag-quick" onClick={() => onPick?.(q.label)}>
            <Ic width={11} height={11} /> {q.label}
          </button>
        );
      })}
    </div>
  );
}

type ComposerProps = {
  value?: string;
  onChange?: (v: string) => void;
  onSend?: (v: string) => void;
  placeholder?: string;
};

export function AgComposer({
  value,
  onChange,
  onSend,
  placeholder = 'Ask Claude to approve, refine, split…',
}: ComposerProps) {
  const ref = useRef<HTMLTextAreaElement>(null);
  const v = value ?? '';
  const submit = () => {
    const text = (ref.current?.value ?? '').trim();
    if (!text) return;
    onSend?.(text);
    if (ref.current) ref.current.value = '';
    onChange?.('');
  };
  useEffect(() => {
    if (!ref.current) return;
    ref.current.style.height = 'auto';
    ref.current.style.height = `${Math.min(120, ref.current.scrollHeight)}px`;
  }, [v]);
  return (
    <div className="ag-composer">
      <div className="ag-composer-box">
        <textarea
          ref={ref}
          rows={1}
          placeholder={placeholder}
          value={v}
          onChange={(e) => onChange?.(e.target.value)}
          onKeyDown={(e) => {
            if (e.key === 'Enter' && !e.shiftKey) {
              e.preventDefault();
              submit();
            }
          }}
        />
        <div className="ag-composer-foot">
          <button type="button" className="ag-iconbtn" style={{ width: 24, height: 24 }} title="Attach">
            <Icon.Attach width={12} height={12} />
          </button>
          <button type="button" className="ag-iconbtn" style={{ width: 24, height: 24 }} title="Voice">
            <Icon.Mic width={12} height={12} />
          </button>
          <span className="ag-composer-hint">
            <span className="ag-kbd" style={{ fontSize: 9.5, padding: '1px 4px' }}>
              ↵
            </span>{' '}
            send
          </span>
          <button
            type="button"
            className="ag-composer-send"
            onClick={submit}
            disabled={!v.trim()}
            title="Send"
          >
            <Icon.Send2 width={13} height={13} />
          </button>
        </div>
      </div>
    </div>
  );
}
