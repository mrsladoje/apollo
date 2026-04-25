import { cn } from '@/lib/utils'
import type { Message, Citation } from '@/types'
import { MessageBubble } from './MessageBubble'

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
