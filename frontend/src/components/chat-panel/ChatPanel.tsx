import { useRef, useEffect, useState } from 'react'
import { cn } from '@/lib/utils'
import { MessageList } from '@/components/message-bubble'
import { useChatContext } from '@/hooks/useChatContext'
import type { Citation } from '@/types'
import { ChatHeader } from './ChatHeader'
import { ChatInput } from './ChatInput'
import { EmptyState } from './EmptyState'
import { SuggestionChip } from './SuggestionChip'

const SUGGESTIONS = [
  'What is the current health of the heating element?',
  'Show me the latest anomaly detections across all components.',
  'When is the next scheduled maintenance predicted?',
]

interface ChatPanelProps {
  onCitationClick?: (citation: Citation) => void
  className?: string
}

export function ChatPanel({ onCitationClick, className }: ChatPanelProps) {
  const { messages, send, clear } = useChatContext()
  const bottomRef = useRef<HTMLDivElement>(null)
  const streaming = messages.some((m) => m.streaming)
  const [inputValue, setInputValue] = useState('')
  const [inputFocused, setInputFocused] = useState(false)

  const showSuggestions = inputFocused && messages.length === 0

  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: 'smooth' })
  }, [messages])

  return (
    <div className={cn('flex flex-col', className)}>
      <ChatHeader onClear={clear} canClear={messages.length > 0 && !streaming} />
      <div className='min-h-0 flex-1 overflow-y-auto py-4'>
        {messages.length === 0 ? (
          <EmptyState />
        ) : (
          <MessageList messages={messages} onCitationClick={onCitationClick} />
        )}
        <div ref={bottomRef} />
      </div>
      <div className='border-t border-border pt-3'>
        {showSuggestions && (
          <div className='flex flex-wrap gap-2 pb-2 px-1'>
            {SUGGESTIONS.map((q) => (
              <SuggestionChip
                key={q}
                text={q}
                onSelect={(text) => setInputValue(text)}
              />
            ))}
          </div>
        )}
        <ChatInput
          value={inputValue}
          onChange={setInputValue}
          onSubmit={send}
          disabled={streaming}
          onFocus={() => setInputFocused(true)}
          onBlur={() => setInputFocused(false)}
        />
      </div>
    </div>
  )
}
