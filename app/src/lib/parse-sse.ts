/**
 * Frame parser for `text/event-stream`.
 *
 * Yields `{ event, data }` per complete `\n\n`-terminated frame. Skips
 * comment lines (`:` prefix) so server-emitted `: keep-alive\n\n` heartbeats
 * never surface as message bubbles.
 */

export type SseFrame = { event: string; data: string };

export type SseParser = {
  push: (chunk: string) => SseFrame[];
  flush: () => SseFrame[];
};

export function createSseParser(): SseParser {
  let buffer = '';

  const drain = (): SseFrame[] => {
    const frames: SseFrame[] = [];
    while (true) {
      const nl = buffer.indexOf('\n\n');
      if (nl < 0) break;
      const block = buffer.slice(0, nl);
      buffer = buffer.slice(nl + 2);
      const frame = parseBlock(block);
      if (frame) frames.push(frame);
    }
    return frames;
  };

  return {
    push: (chunk: string) => {
      buffer += chunk;
      return drain();
    },
    flush: () => drain(),
  };
}

function parseBlock(block: string): SseFrame | null {
  // All-comment block (e.g. `: keep-alive`) → skip.
  let event = 'message';
  const dataLines: string[] = [];
  let sawNonComment = false;
  for (const raw of block.split('\n')) {
    const line = raw.endsWith('\r') ? raw.slice(0, -1) : raw;
    if (line === '') continue;
    if (line.startsWith(':')) continue;
    sawNonComment = true;
    if (line.startsWith('event:')) {
      event = line.slice('event:'.length).trim();
    } else if (line.startsWith('data:')) {
      dataLines.push(line.slice('data:'.length).trim());
    }
  }
  if (!sawNonComment) return null;
  return { event, data: dataLines.join('\n') };
}
