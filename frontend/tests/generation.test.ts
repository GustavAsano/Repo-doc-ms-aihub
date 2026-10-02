import { describe, expect, mock, test } from 'bun:test';

mock.module('@/utils/const', () => ({ default: { backendHost: 'http://localhost', backendPort: '8000', backendBase: '', apiKey: '' } }));
const { generateDocs } = await import('../src/services/backend');

const result = {
  repo_name: 'example', language: 'PT-BR', docs_generated: true,
  functional_docs_generated: true, doc_variant: 'technical',
  generation_mode: 'technical_and_functional', docs_skipped: false,
};

async function consume(chunks: string[]) {
  const encoder = new TextEncoder();
  const stream = new ReadableStream({
    start(controller) {
      for (const chunk of chunks) controller.enqueue(encoder.encode(chunk));
      controller.close();
    },
  });
  globalThis.fetch = mock(async () => new Response(stream)) as unknown as typeof fetch;
  const events: Record<string, unknown>[] = [];
  return new Promise<{ result?: unknown; error?: string; events: Record<string, unknown>[] }>((resolve) => {
    generateDocs({ repo_name: 'example', language: 'PT-BR', generation_mode: 'technical_and_functional',
      provider: 'bedrock', model: 'test', use_system_key: true },
    event => events.push(event),
    state => resolve({ result: state, events }),
    error => resolve({ error, events }));
  });
}
const sse = (data: unknown) => `data: ${JSON.stringify(data)}\n\n`;

describe('generation stream', () => {
  test('waits for API result after intermediate technical completion', async () => {
    const response = await consume([
      sse({ event: 'phase_done', doc_variant: 'technical' }),
      sse({ event: 'done', phase: 'done' }), // legacy stage done has no result
      sse({ event: 'call_end', doc_variant: 'functional', current_call: 21 }),
      sse({ event: 'done', result }),
    ]);
    expect(response.result).toEqual(result);
    expect(response.events).toHaveLength(4);
    expect(response.error).toBeUndefined();
  });
  test('truncated stream does not report success', async () => {
    const response = await consume([sse({ event: 'phase_done', doc_variant: 'technical' })]);
    expect(response.result).toBeUndefined();
    expect(response.error).toContain('before completion');
  });
  test('functional error after technical completion is surfaced', async () => {
    const response = await consume([sse({ event: 'phase_done' }), sse({ event: 'error', message: 'Functional failed' })]);
    expect(response.error).toBe('Functional failed');
    expect(response.result).toBeUndefined();
  });
  test('split SSE chunks preserve functional-only result', async () => {
    const functional = { ...result, docs_generated: false, doc_variant: 'functional', generation_mode: 'functional_only' };
    const message = sse({ event: 'done', result: functional });
    const response = await consume([message.slice(0, 7), message.slice(7, 35), message.slice(35)]);
    expect(response.result).toEqual(functional);
  });
});
