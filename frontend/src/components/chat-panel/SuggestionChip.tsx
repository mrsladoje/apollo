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
        'rounded-full border px-3 py-1.5 text-left text-[11px] text-muted-foreground transition-colors duration-200',
        'hover:border-[rgba(0,150,214,0.4)] hover:bg-[rgba(0,150,214,0.05)] hover:text-[#0073A8]',
        className,
      )}
      style={{
        borderColor: 'rgb(225 230 236)',
        background: '#FFFFFF',
      }}
    >
      {text}
    </button>
  )
}
