import { ExternalLink } from 'lucide-react'
import { cn } from '@/lib/utils'
import { SeverityBadge } from '@/components/severity-badge'
import { CitationList } from '@/components/citation-chip'
import { ToolCallList } from '@/components/tool-call-card'
import type { Message, Citation } from '@/types'
import { ApolloAvatar } from './ApolloAvatar'

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
        <p
          className='max-w-[78%] rounded-2xl rounded-tr-sm px-4 py-2 text-[13px] leading-relaxed text-foreground/90'
          style={{
            background: 'rgba(0,150,214,0.06)',
            border: '1px solid rgba(0,150,214,0.16)',
          }}
        >
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
              <span
                className='h-1.5 w-1.5 animate-hp-pulse rounded-full'
                style={{ background: '#0096D6' }}
              />
            )}
          </div>

          {message.tool_calls.length > 0 && (
            <ToolCallList toolCalls={message.tool_calls} />
          )}

          <p
            className={cn(
              'text-[13px] leading-relaxed',
              isRefusal ? 'text-muted-foreground' : 'text-foreground',
            )}
          >
            {message.text}
            {message.streaming && (
              <span
                className='ml-0.5 animate-hp-pulse'
                style={{ color: '#0096D6' }}
              >
                ▋
              </span>
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
              className='hp-link inline-flex items-center gap-1 font-mono text-[10px] tracking-wider text-muted-foreground hover:text-[#0073A8]'
            >
              Trace <ExternalLink className='h-2.5 w-2.5' />
            </a>
          )}
        </div>
      </div>
    </div>
  )
}
