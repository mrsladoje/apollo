import { cn } from '@/lib/utils'

interface ResizeHandleProps {
  onResize: (width: number) => void
  className?: string
}

export function ResizeHandle({ onResize, className }: ResizeHandleProps) {
  const handleMouseDown = () => {
    const onMouseMove = (e: MouseEvent) => {
      const newWidth = Math.min(
        600,
        Math.max(260, window.innerWidth - e.clientX),
      )
      onResize(newWidth)
    }
    const onMouseUp = () => {
      document.removeEventListener('mousemove', onMouseMove)
      document.removeEventListener('mouseup', onMouseUp)
    }
    document.addEventListener('mousemove', onMouseMove)
    document.addEventListener('mouseup', onMouseUp)
  }

  return (
    <div
      role='separator'
      aria-orientation='vertical'
      tabIndex={0}
      onMouseDown={handleMouseDown}
      className={cn(
        'hidden md:flex w-1 shrink-0 cursor-col-resize items-center justify-center',
        'border-l border-border hover:border-primary/40 transition-colors',
        className,
      )}
    />
  )
}
