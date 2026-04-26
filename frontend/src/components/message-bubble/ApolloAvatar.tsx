import { cn } from '@/lib/utils'

interface ApolloAvatarProps {
  className?: string
}

export function ApolloAvatar({ className }: ApolloAvatarProps) {
  return (
    <div
      className={cn(
        'relative flex h-6 w-6 shrink-0 items-center justify-center rounded-full',
        className,
      )}
      style={{
        background: 'linear-gradient(135deg, #33A8DD 0%, #0096D6 60%, #0073A8 100%)',
        boxShadow:
          '0 1px 0 rgba(255,255,255,0.35) inset,' +
          '0 4px 12px -4px rgba(0,150,214,0.55)',
      }}
    >
      <span
        className='font-sans text-[11px] font-bold leading-none'
        style={{
          color: '#FFFFFF',
          letterSpacing: '0.02em',
          transform: 'translateY(-0.5px)',
        }}
      >
        A
      </span>
    </div>
  )
}
