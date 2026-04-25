import { cn } from '@/lib/utils'
import { SuggestedQuestion } from './SuggestedQuestion'

const SUGGESTED = [
  'How is the Barcelona run performing?',
  'When did the Dark Twin lose its first component?',
  'Compare heater health across all three universes.',
]

interface SuggestedQuestionsProps {
  className?: string
}

export function SuggestedQuestions({ className }: SuggestedQuestionsProps) {
  return (
    <div className={cn('flex flex-col gap-1', className)}>
      {SUGGESTED.map((q) => (
        <SuggestedQuestion key={q} text={q} />
      ))}
    </div>
  )
}
