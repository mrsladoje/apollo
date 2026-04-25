import { useCallback, useEffect, useRef, useState } from 'react'
import { Send } from 'lucide-react'
import { cn } from '@/lib/utils'

interface ChatInputProps {
  readonly value?: string
  readonly onChange?: (value: string) => void
  readonly className?: string
  readonly onSubmit?: (message: string) => void | Promise<void>
  readonly disabled?: boolean
}

export function ChatInput({
  value,
  onChange,
  onSubmit,
  className,
  disabled,
}: ChatInputProps) {
  const [internalValue, setInternalValue] = useState('')
  const inputRef = useRef<HTMLTextAreaElement>(null)
  const isControlled = value !== undefined
  const currentValue = isControlled ? value : internalValue

  // Auto-resize textarea to fit content
  const resize = useCallback(() => {
    const el = inputRef.current
    if (!el) return
    el.style.height = 'auto'
    el.style.height = `${el.scrollHeight}px`
  }, [])

  const handleChange = (e: React.ChangeEvent<HTMLTextAreaElement>) => {
    if (disabled) return
    const nextValue = e.currentTarget.value
    if (!isControlled) setInternalValue(nextValue)
    onChange?.(nextValue)
    resize()
  }

  const clearInput = useCallback(() => {
    if (!isControlled) setInternalValue('')
    onChange?.('')
    if (inputRef.current) {
      inputRef.current.value = ''
      inputRef.current.style.height = 'auto'
      inputRef.current.focus()
    }
  }, [isControlled, onChange])

  const handleSubmit = useCallback(
    async (e?: React.FormEvent<HTMLFormElement>) => {
      e?.preventDefault()
      if (disabled || !onSubmit) return
      const message = (inputRef.current?.value ?? currentValue ?? '').trim()
      if (!message) return
      clearInput()
      try {
        await onSubmit(message)
      } catch {
        if (inputRef.current) inputRef.current.value = message
      }
    },
    [clearInput, currentValue, disabled, onSubmit],
  )

  const handleKeyDown = (e: React.KeyboardEvent<HTMLTextAreaElement>) => {
    if (disabled) return
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault()
      void handleSubmit()
    }
  }

  // Sync controlled value into the textarea
  useEffect(() => {
    if (
      isControlled &&
      inputRef.current &&
      inputRef.current.value !== (value ?? '')
    ) {
      inputRef.current.value = value ?? ''
      resize()
    }
  }, [isControlled, value, resize])

  // Auto-focus on mount
  useEffect(() => {
    if (!disabled) inputRef.current?.focus()
  }, [disabled])

  return (
    <form
      className={cn(
        'flex items-end gap-2',
        disabled && 'pointer-events-none opacity-50',
        className,
      )}
      onSubmit={handleSubmit}
    >
      <textarea
        ref={inputRef}
        rows={1}
        placeholder='Ask Apollo…'
        defaultValue={isControlled ? undefined : internalValue}
        onChange={handleChange}
        onKeyDown={handleKeyDown}
        className='flex-1 resize-none overflow-hidden bg-transparent text-sm text-foreground placeholder:text-muted-foreground outline-none'
      />
      <button
        type='submit'
        disabled={disabled}
        className='shrink-0 pb-0.5 text-muted-foreground transition-colors hover:text-foreground disabled:opacity-30'
      >
        <Send className='h-3.5 w-3.5' />
      </button>
    </form>
  )
}
