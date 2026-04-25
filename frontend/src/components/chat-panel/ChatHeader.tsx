import { cn } from '@/lib/utils'

interface ChatHeaderProps {
  className?: string
}

export function ChatHeader({ className }: ChatHeaderProps) {
  return (
    <div className={cn('pb-3 border-b border-border', className)}>
      <p className='text-xs font-semibold uppercase tracking-widest text-muted-foreground'>
        Apollo
      </p>
    </div>
  )
}
