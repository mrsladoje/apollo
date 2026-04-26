import { cn } from '@/lib/utils'

interface SuggestionChipProps {
  text: string
  onSelect: (text: string) => void
  className?: string
}

export function SuggestionChip({
  text,
  onSelect,
  className,
}: SuggestionChipProps) {
  return (
    <button
      type='button'
      onClick={() => onSelect(text)}
      className={cn(
        'rounded-full border border-border bg-background px-3 py-1.5 text-left text-xs text-muted-foreground',
        'transition-colors hover:border-blue-300 hover:bg-blue-50 hover:text-blue-700',
        className,
      )}
    >
      {text}
    </button>
  )
}
