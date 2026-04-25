import * as React from 'react'
import { cn } from '@/lib/utils'

const Separator = React.forwardRef<
  HTMLHRElement,
  React.HTMLAttributes<HTMLHRElement> & {
    orientation?: 'horizontal' | 'vertical'
    decorative?: boolean
  }
>(
  (
    { className, orientation = 'horizontal', decorative = true, ...props },
    ref,
  ) => (
    <hr
      ref={ref}
      role={decorative ? 'none' : 'separator'}
      aria-orientation={decorative ? undefined : orientation}
      className={cn(
        'shrink-0 border-border',
        orientation === 'horizontal'
          ? 'h-[1px] w-full border-t'
          : 'h-full w-[1px] border-l',
        className,
      )}
      {...props}
    />
  ),
)
Separator.displayName = 'Separator'

export { Separator }
