/**
 * SSE-driven chat hook against POST /runs/{id}/chat.
 *
 * `send` opens a fetch stream with an AbortController; subsequent `send`s
 * abort the previous one. Heartbeats (`: keep-alive`) are dropped by the
 * parser. Single-deletion revisions auto-apply via `onRevision`; bulk
 * deletions surface as a pending preview to be Accepted/Rejected.
 */

import { useCallback, useEffect, useRef, useState } from 'react';
import { apiFetch, apiJson, ApiError } from '../auth';
import { createSseParser, type SseFrame } from '../lib/parse-sse';
import type { StoriesOutput, Story } from '../lib/story-types';

export type ChatMessage = {
  id: string;
  role: 'user' | 'assistant';
  content: string;
  revisionVersion: number | null;
  status: 'streaming' | 'done' | 'error';
  errorDetail?: string | null;
};

export type BulkPreview = {
  previewId: string;
  storiesPayload: StoriesOutput;
  removedIds: string[];
};

type HistoryTurn = {
  id: number;
  role: 'user' | 'assistant';
  content: string;
  revision_version: number | null;
  status: 'streaming' | 'done' | 'error';
  error_detail: string | null;
  created_at: string;
};

type RevisionPayload = { version: number; stories: StoriesOutput; removed_ids: string[] };
type RevisionPreviewPayload = { preview_id: string; stories: StoriesOutput; removed_ids: string[] };

export type UseChat = {
  messages: ChatMessage[];
  streaming: boolean;
  error: string | null;
  preview: BulkPreview | null;
  send: (text: string) => Promise<void>;
  cancel: () => void;
  restore: (version: number) => Promise<void>;
  acceptPreview: (previewId: string) => Promise<void>;
  rejectPreview: () => void;
  clearHistory: () => Promise<void>;
  reload: () => void;
};

export function useChat(
  runId: string | null,
  onRevision?: (stories: Story[]) => void,
): UseChat {
  const [messages, setMessages] = useState<ChatMessage[]>([]);
  const [streaming, setStreaming] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [preview, setPreview] = useState<BulkPreview | null>(null);
  const [version, setVersion] = useState(0);
  const controllerRef = useRef<AbortController | null>(null);
  const cancelled = useRef(false);

  useEffect(() => {
    cancelled.current = false;
    setMessages([]);
    setError(null);
    setPreview(null);
    if (!runId) return () => { cancelled.current = true; };

    apiJson<{ turns: HistoryTurn[] }>(`/runs/${runId}/chat/history`)
      .then((data) => {
        if (cancelled.current) return;
        setMessages(data.turns.map((t, idx) => ({
          id: `srv-${t.id ?? idx}`,
          role: t.role,
          content: t.content,
          revisionVersion: t.revision_version,
          status: t.status,
          errorDetail: t.error_detail,
        })));
      })
      .catch((e) => {
        if (cancelled.current) return;
        setError(e instanceof ApiError ? `${e.status}` : (e as Error).message);
      });

    return () => {
      cancelled.current = true;
      controllerRef.current?.abort();
    };
  }, [runId, version]);

  const send = useCallback(async (text: string) => {
    if (!runId || !text.trim()) return;
    controllerRef.current?.abort();
    const controller = new AbortController();
    controllerRef.current = controller;
    setError(null);
    setPreview(null);

    const userMsg: ChatMessage = {
      id: `local-u-${Date.now()}`,
      role: 'user',
      content: text,
      revisionVersion: null,
      status: 'done',
    };
    const asstId = `local-a-${Date.now()}`;
    const asstMsg: ChatMessage = {
      id: asstId,
      role: 'assistant',
      content: '',
      revisionVersion: null,
      status: 'streaming',
    };
    setMessages((prev) => [...prev, userMsg, asstMsg]);
    setStreaming(true);

    try {
      const res = await apiFetch(`/runs/${runId}/chat`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          Accept: 'text/event-stream',
        },
        body: JSON.stringify({ message: text }),
        signal: controller.signal,
      });
      if (!res.ok || !res.body) {
        throw new Error(`chat ${res.status}`);
      }
      const reader = res.body.getReader();
      const decoder = new TextDecoder('utf-8');
      const parser = createSseParser();
      while (true) {
        if (controller.signal.aborted) {
          reader.cancel().catch(() => {});
          break;
        }
        const { done, value } = await reader.read();
        if (done) break;
        const frames = parser.push(decoder.decode(value, { stream: true }));
        for (const f of frames) handleFrame(f, asstId);
      }
      for (const f of parser.flush()) handleFrame(f, asstId);
    } catch (e) {
      if (controller.signal.aborted) {
        // user-requested cancel — leave the message as it stands
      } else {
        setError((e as Error).message);
        setMessages((prev) => prev.map((m) =>
          m.id === asstId ? { ...m, status: 'error', errorDetail: (e as Error).message } : m,
        ));
      }
    } finally {
      setStreaming(false);
      if (controllerRef.current === controller) controllerRef.current = null;
    }

    function handleFrame(frame: SseFrame, assistantId: string): void {
      try {
        if (frame.event === 'text') {
          const delta = JSON.parse(frame.data) as string;
          setMessages((prev) => prev.map((m) =>
            m.id === assistantId ? { ...m, content: m.content + delta } : m,
          ));
        } else if (frame.event === 'revision') {
          const r = JSON.parse(frame.data) as RevisionPayload;
          setMessages((prev) => prev.map((m) =>
            m.id === assistantId ? { ...m, revisionVersion: r.version } : m,
          ));
          onRevision?.(r.stories.stories);
        } else if (frame.event === 'revision_preview') {
          const p = JSON.parse(frame.data) as RevisionPreviewPayload;
          setPreview({
            previewId: p.preview_id,
            storiesPayload: p.stories,
            removedIds: p.removed_ids,
          });
        } else if (frame.event === 'error') {
          const detail = JSON.parse(frame.data) as { detail: string };
          setError(detail.detail);
          setMessages((prev) => prev.map((m) =>
            m.id === assistantId ? { ...m, status: 'error', errorDetail: detail.detail } : m,
          ));
        } else if (frame.event === 'done') {
          setMessages((prev) => prev.map((m) =>
            m.id === assistantId ? { ...m, status: 'done' } : m,
          ));
        }
      } catch (e) {
        setError((e as Error).message);
      }
    }
  }, [runId, onRevision]);

  const cancel = useCallback(() => {
    controllerRef.current?.abort();
  }, []);

  const restore = useCallback(async (revisionVersion: number) => {
    if (!runId) return;
    try {
      const res = await apiJson<{ version: number }>(
        `/runs/${runId}/chat/revisions/${revisionVersion}/restore`,
        { method: 'POST' },
      );
      // Refetch the new revision's stories.
      const stories = await apiJson<StoriesOutput>(`/runs/${runId}/files/stories.json`);
      onRevision?.(stories.stories);
      // Mark a synthetic assistant turn so the user sees what happened.
      setMessages((prev) => [...prev, {
        id: `local-restore-${Date.now()}`,
        role: 'assistant',
        content: `Restored revision ${revisionVersion} (now version ${res.version}).`,
        revisionVersion: res.version,
        status: 'done',
      }]);
    } catch (e) {
      setError((e as Error).message);
    }
  }, [runId, onRevision]);

  const acceptPreview = useCallback(async (previewId: string) => {
    if (!runId) return;
    try {
      await apiJson<{ version: number }>(
        `/runs/${runId}/chat/revisions/preview/${previewId}/accept`,
        { method: 'POST' },
      );
      const stories = await apiJson<StoriesOutput>(`/runs/${runId}/files/stories.json`);
      onRevision?.(stories.stories);
      setPreview(null);
    } catch (e) {
      setError((e as Error).message);
    }
  }, [runId, onRevision]);

  const rejectPreview = useCallback(() => {
    setPreview(null);
  }, []);

  const clearHistory = useCallback(async () => {
    if (!runId) return;
    try {
      await apiJson(`/runs/${runId}/chat/history`, { method: 'DELETE' });
      setMessages([]);
    } catch (e) {
      setError((e as Error).message);
    }
  }, [runId]);

  return {
    messages,
    streaming,
    error,
    preview,
    send,
    cancel,
    restore,
    acceptPreview,
    rejectPreview,
    clearHistory,
    reload: () => setVersion((v) => v + 1),
  };
}
