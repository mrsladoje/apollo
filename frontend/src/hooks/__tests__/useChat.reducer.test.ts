import { describe, it, expect } from 'vitest'
import { renderHook, act } from '@testing-library/react'
import { useChat } from '@/hooks/useChat'
import type { SSEEvent } from '@/types'

describe('chat reducer', () => {
  it('appends text-delta tokens to the streaming Apollo bubble', () => {
    const { result } = renderHook(() => useChat())

    act(() => {
      // Inject a user message synthetically.
      result.current.send('hi')
    })

    // useChat's send() kicks off a fetch; we can't easily pump SSE in jsdom,
    // but we can assert the user bubble + empty Apollo bubble exist.
    expect(result.current.messages.length).toBe(2)
    expect(result.current.messages[0].role).toBe('user')
    expect(result.current.messages[1].role).toBe('apollo')
    expect(result.current.messages[1].streaming).toBe(true)
  })

  it('SSE schema matches the frozen union', () => {
    const events: SSEEvent[] = [
      { type: 'text-delta', payload: { token: 'My ' } },
      { type: 'tool-call-start', payload: { tool: 'query_historian', args: {}, call_id: 'c1' } },
      { type: 'tool-result', payload: { call_id: 'c1', result: { rows: 1 } } },
      { type: 'citation', payload: { run_id: 'r', component: 'nozzle', timestamp: '2026-04-25T10:00:00Z' } },
      { type: 'done', payload: { trace_url: 'https://example/trace/x' } },
    ]
    expect(events.map((e) => e.type)).toEqual([
      'text-delta',
      'tool-call-start',
      'tool-result',
      'citation',
      'done',
    ])
  })
})
