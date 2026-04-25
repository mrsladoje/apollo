import { useRef, useEffect } from 'react'
import { Send } from 'lucide-react'
import { cn } from '@/lib/utils'
import { MessageList } from '@/components/MessageBubble'
import { useChat } from '@/hooks/useChat'
import type { Citation } from '@/types'
import { useState } from 'react'

interface ChatInputProps {
  onSend: (query: string) => void
  disabled?: boolean
  className?: string
}

function ChatInput({ onSend, disabled, className }: ChatInputProps) {
  const [value, setValue] = useState('')

  function handleSubmit(e: React.FormEvent) {
    e.preventDefault()
    if (!value.trim()) return
    onSend(value.trim())
    setValue('')
  }

  return (
    <form
      onSubmit={handleSubmit}
      className={cn('flex items-center gap-2', className)}
    >
      <input
        value={value}
        onChange={(e) => setValue(e.target.value)}
        disabled={disabled}
        placeholder='Ask Apollo…'
        className='flex-1 bg-transparent text-sm text-foreground placeholder:text-muted-foreground outline-none'
      />
      <button
        type='submit'
        disabled={!value.trim() || disabled}
        className='text-muted-foreground transition-colors hover:text-foreground disabled:opacity-30'
      >
        <Send className='h-3.5 w-3.5' />
      </button>
    </form>
  )
}

interface ChatPanelProps {
  onCitationClick?: (citation: Citation) => void
  className?: string
}

export function ChatPanel({ onCitationClick, className }: ChatPanelProps) {
  const { messages, send } = useChat()
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
      <div className='border-t border-border py-3'>
        <ChatInput onSend={send} disabled={streaming} />
      </div>
    </div>
  )
}

function ChatHeader({ className }: { className?: string }) {
  return (
    <div className={cn('pb-3 border-b border-border', className)}>
      <p className='text-xs font-semibold uppercase tracking-widest text-muted-foreground'>
        Apollo
      </p>
    </div>
  )
}

function EmptyState({ className }: { className?: string }) {
  return (
    <div className={cn('flex flex-col items-start gap-4 py-8', className)}>
      <p className='text-sm text-muted-foreground'>
        Ask me anything about the HP Metal Jet S100 telemetry.
      </p>
      <SuggestedQuestions />
    </div>
  )
}

interface SuggestedQuestionsProps {
  className?: string
}

function SuggestedQuestions({ className }: SuggestedQuestionsProps) {
  return (
    <div className={cn('flex flex-col gap-1', className)}>
      {SUGGESTED.map((q) => (
        <SuggestedQuestion key={q} text={q} />
      ))}
    </div>
  )
}

interface SuggestedQuestionProps {
  text: string
  className?: string
}

function SuggestedQuestion({ text, className }: SuggestedQuestionProps) {
  return (
    <p className={cn('text-[11px] text-muted-foreground/60', className)}>
      ↳ {text}
    </p>
  )
}

const SUGGESTED = [
  'How is the Barcelona run performing?',
  'When did the Dark Twin lose its first component?',
  'Compare heater health across all three universes.',
]
