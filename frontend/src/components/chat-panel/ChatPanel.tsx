import { useRef, useEffect } from 'react'
import { cn } from '@/lib/utils'
import { MessageList } from '@/components/message-bubble'
import { useChatContext } from '@/hooks/useChatContext'
import type { Citation } from '@/types'
import { ChatHeader } from './ChatHeader'
import { ChatInput } from './ChatInput'
import { EmptyState } from './EmptyState'

interface ChatPanelProps {
  onCitationClick?: (citation: Citation) => void
  className?: string
}

export function ChatPanel({ onCitationClick, className }: ChatPanelProps) {
  const { messages, send } = useChatContext()
  const bottomRef = useRef<HTMLDivElement>(null)
  const streaming = messages.some((m) => m.streaming)

  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: 'smooth' })
  }, [messages])

  return (
    <div className={cn('flex flex-col', className)}>
      <ChatHeader />
      <div className='min-h-0 flex-1 overflow-y-auto py-4'>
        {messages.length === 0 ? (
          <EmptyState />
        ) : (
          <MessageList messages={messages} onCitationClick={onCitationClick} />
        )}
        <div ref={bottomRef} />
      </div>
      <div className='border-t border-border pt-3'>
        <ChatInput onSubmit={send} disabled={streaming} />
      </div>
    </div>
  )
}
