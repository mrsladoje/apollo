import { MessageSquareIcon } from 'lucide-react'
import { cn } from '@/lib/utils'

interface ChatDrawerTriggerProps {
  onOpen: () => void
  className?: string
}

export function ChatDrawerTrigger({
  onOpen,
  className,
}: ChatDrawerTriggerProps) {
  return (
    <button
      onClick={onOpen}
      className={cn(
        'fixed bottom-4 right-4 z-40 flex size-12 items-center justify-center',
        'rounded-full bg-primary text-primary-foreground shadow-lg',
        'hover:bg-primary/90 transition-colors md:hidden',
        className,
      )}
      aria-label='Open chat'
    >
      <MessageSquareIcon className='size-5' />
    </button>
  )
}
