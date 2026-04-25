import { ExternalLink } from 'lucide-react'
import { cn } from '@/lib/utils'
import { SeverityBadge } from '@/components/SeverityBadge'
import { CitationList } from '@/components/CitationChip'
import { ToolCallList } from '@/components/ToolCallCard'
import type { Message, Citation } from '@/types'

interface MessageBubbleProps {
  message: Message
  onCitationClick?: (citation: Citation) => void
  className?: string
}

export function MessageBubble({
  message,
  onCitationClick,
  className,
}: MessageBubbleProps) {
  if (message.role === 'user') {
    return (
      <div className={cn('flex justify-end', className)}>
        <p className='max-w-[75%] text-sm text-muted-foreground'>
          {message.text}
        </p>
      </div>
    )
  }

  const isRefusal =
    message.severity === 'REFUSAL' || message.text.startsWith('REFUSAL')

  return (
    <div className={cn('space-y-3', className)}>
      <div className='flex items-start gap-3'>
        <ApolloAvatar />
        <div className='min-w-0 flex-1 space-y-2'>
          <div className='flex items-center gap-2'>
            {message.severity && <SeverityBadge severity={message.severity} />}
            {message.streaming && (
              <span className='h-1.5 w-1.5 animate-pulse rounded-full bg-primary/60' />
            )}
          </div>

          {message.tool_calls.length > 0 && (
            <ToolCallList toolCalls={message.tool_calls} />
          )}

          <p
            className={cn(
              'text-sm leading-relaxed',
              isRefusal ? 'text-muted-foreground' : 'text-foreground',
            )}
          >
            {message.text}
            {message.streaming && (
              <span className='ml-0.5 animate-pulse'>▋</span>
            )}
          </p>

          {!isRefusal && (
            <CitationList
              citations={message.citations}
              onCitationClick={onCitationClick}
            />
          )}

          {message.trace_url && (
            <a
              href={message.trace_url}
              target='_blank'
              rel='noopener noreferrer'
              className='inline-flex items-center gap-1 text-[10px] text-muted-foreground underline-offset-2 hover:text-foreground hover:underline'
            >
              Trace <ExternalLink className='h-2.5 w-2.5' />
            </a>
          )}
        </div>
      </div>
    </div>
  )
}

function ApolloAvatar({ className }: { className?: string }) {
  return (
    <div
      className={cn(
        'flex h-6 w-6 shrink-0 items-center justify-center rounded-full bg-primary/10 text-[10px] font-bold text-primary',
        className,
      )}
    >
      A
    </div>
  )
}

interface MessageListProps {
  messages: Message[]
  onCitationClick?: (citation: Citation) => void
  className?: string
}

export function MessageList({
  messages,
  onCitationClick,
  className,
}: MessageListProps) {
  return (
    <div className={cn('space-y-6', className)}>
      {messages.map((m) => (
        <MessageBubble
          key={m.id}
          message={m}
          onCitationClick={onCitationClick}
        />
      ))}
    </div>
  )
}
