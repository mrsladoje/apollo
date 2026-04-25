import { useCallback, useReducer, useRef } from 'react'
import type { Message, SSEEvent, Citation, ToolCall } from '@/types'

type ChatState = { messages: Message[] }

type Action = { type: 'user'; text: string } | { type: 'sse'; event: SSEEvent }

let msgCounter = 0
function newId() {
  return `msg-${++msgCounter}`
}

function emptyApolloMsg(): Message {
  return {
    id: newId(),
    role: 'apollo',
    text: '',
    citations: [],
    tool_calls: [],
    streaming: true,
  }
}

function chatReducer(state: ChatState, action: Action): ChatState {
  if (action.type === 'user') {
    return {
      messages: [
        ...state.messages,
        {
          id: newId(),
          role: 'user',
          text: action.text,
          citations: [],
          tool_calls: [],
          streaming: false,
        },
        emptyApolloMsg(),
      ],
    }
  }

  const msgs = [...state.messages]
  const last = msgs[msgs.length - 1]
  if (!last || last.role !== 'apollo') return state

  const ev = action.event
  switch (ev.type) {
    case 'text-delta':
      msgs[msgs.length - 1] = { ...last, text: last.text + ev.payload.token }
      break
    case 'tool-call-start': {
      const tc: ToolCall = {
        tool: ev.payload.tool as ToolCall['tool'],
        args: ev.payload.args as Record<string, unknown>,
        result: null,
        call_id: ev.payload.call_id,
        started_at: new Date().toISOString(),
        finished_at: null,
      }
      msgs[msgs.length - 1] = { ...last, tool_calls: [...last.tool_calls, tc] }
      break
    }
    case 'tool-result': {
      const updated = last.tool_calls.map((tc) =>
        tc.call_id === ev.payload.call_id
          ? {
              ...tc,
              result: ev.payload.result as Record<string, unknown>,
              finished_at: new Date().toISOString(),
            }
          : tc,
      )
      msgs[msgs.length - 1] = { ...last, tool_calls: updated }
      break
    }
    case 'citation': {
      const cit: Citation = ev.payload
      msgs[msgs.length - 1] = { ...last, citations: [...last.citations, cit] }
      break
    }
    case 'done':
      msgs[msgs.length - 1] = {
        ...last,
        trace_url: ev.payload.trace_url,
        streaming: false,
        severity: last.text.startsWith('REFUSAL')
          ? 'REFUSAL'
          : (last.severity ?? 'INFO'),
      }
      break
  }

  return { messages: msgs }
}

export function useChat() {
  const [state, dispatch] = useReducer(chatReducer, { messages: [] })
  const abortRef = useRef<(() => void) | null>(null)

  const send = useCallback((query: string) => {
    if (abortRef.current) abortRef.current()
    dispatch({ type: 'user', text: query })

    const es = new EventSource(`/api/chat?query=${encodeURIComponent(query)}`)

    // POST via fetch + read the SSE stream
    const ctrl = new AbortController()
    abortRef.current = () => ctrl.abort()

    fetch('/api/chat', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ query }),
      signal: ctrl.signal,
    })
      .then(async (res) => {
        es.close()
        const reader = res.body?.getReader()
        if (!reader) return
        const decoder = new TextDecoder()
        let buffer = ''
        while (true) {
          const { done, value } = await reader.read()
          if (done) break
          buffer += decoder.decode(value, { stream: true })
          const lines = buffer.split('\n')
          buffer = lines.pop() ?? ''
          for (const line of lines) {
            if (line.startsWith('data: ')) {
              try {
                const event: SSEEvent = JSON.parse(line.slice(6))
                dispatch({ type: 'sse', event })
              } catch {
                // ignore parse errors
              }
            }
          }
        }
      })
      .catch(() => {
        /* aborted */
      })

    es.close()
  }, [])

  return { messages: state.messages, send }
}
