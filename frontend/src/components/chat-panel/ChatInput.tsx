import { useCallback, useEffect, useRef, useState } from 'react'
import { ArrowUp } from 'lucide-react'
import { cn } from '@/lib/utils'

interface ChatInputProps {
  readonly value?: string
  readonly onChange?: (value: string) => void
  readonly className?: string
  readonly onSubmit?: (message: string) => void | Promise<void>
  readonly disabled?: boolean
  readonly onFocus?: () => void
  readonly onBlur?: () => void
}

export function ChatInput({
  value,
  onChange,
  onSubmit,
  className,
  disabled,
  onFocus,
  onBlur,
}: ChatInputProps) {
  const [internalValue, setInternalValue] = useState('')
  const [hasContent, setHasContent] = useState(false)
  const inputRef = useRef<HTMLTextAreaElement>(null)
  const isControlled = value !== undefined
  const currentValue = isControlled ? value : internalValue

  const resize = useCallback(() => {
    const el = inputRef.current
    if (!el) return
    el.style.height = 'auto'
    el.style.height = `${el.scrollHeight}px`
    setHasContent(el.value.trim().length > 0)
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
    setHasContent(false)
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
        className='flex-1 resize-none overflow-hidden bg-transparent font-sans text-[13px] leading-relaxed text-foreground placeholder:text-muted-foreground/55 outline-none'
        onFocus={onFocus}
        onBlur={onBlur}
      />
      <button
        type='submit'
        disabled={disabled || !hasContent}
        aria-label='Send message'
        className={cn(
          'flex h-7 w-7 shrink-0 items-center justify-center rounded-full transition-all duration-200',
          'disabled:cursor-not-allowed disabled:opacity-30',
        )}
        style={{
          background: hasContent
            ? 'linear-gradient(180deg, #0096D6 0%, #0073A8 100%)'
            : 'rgb(225 230 236)',
          boxShadow: hasContent
            ? '0 1px 0 rgba(255,255,255,0.2) inset, 0 4px 14px -4px rgba(0,150,214,0.55)'
            : 'none',
        }}
      >
        <ArrowUp
          className='h-3.5 w-3.5'
          style={{
            color: hasContent ? '#FFFFFF' : '#94A3B8',
            strokeWidth: 2.4,
          }}
        />
      </button>
    </form>
  )
}
