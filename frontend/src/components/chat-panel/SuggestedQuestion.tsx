import { cn } from '@/lib/utils'

interface SuggestedQuestionProps {
  text: string
  className?: string
}

export function SuggestedQuestion({ text, className }: SuggestedQuestionProps) {
  return (
    <p className={cn('text-[11px] text-muted-foreground/60', className)}>
      ↳ {text}
    </p>
  )
}
