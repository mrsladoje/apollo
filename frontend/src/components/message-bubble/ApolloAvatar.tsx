import { cn } from '@/lib/utils'

interface ApolloAvatarProps {
  className?: string
}

export function ApolloAvatar({ className }: ApolloAvatarProps) {
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
