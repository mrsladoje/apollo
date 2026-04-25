import { XIcon } from 'lucide-react'
import { Drawer } from '@base-ui/react/drawer'
import { ChatPanel } from '@/components/chat-panel'
import { cn } from '@/lib/utils'

interface ChatDrawerProps {
  open: boolean
  onOpenChange: (open: boolean) => void
  className?: string
}

export function ChatDrawer({ open, onOpenChange, className }: ChatDrawerProps) {
  return (
    <Drawer.Root open={open} onOpenChange={onOpenChange} swipeDirection='right'>
      <Drawer.Portal>
        <Drawer.Backdrop
          className={cn(
            'fixed inset-0 z-40 bg-black/50',
            'data-[open]:animate-in data-[closed]:animate-out',
            'data-[open]:fade-in-0 data-[closed]:fade-out-0',
          )}
        />
        <Drawer.Popup
          className={cn(
            'fixed inset-y-0 right-0 z-50 flex w-[min(380px,100vw)] flex-col',
            'border-l border-border bg-background px-6 py-6',
            'data-[open]:animate-in data-[closed]:animate-out',
            'data-[open]:slide-in-from-right data-[closed]:slide-out-to-right',
            'duration-300',
            className,
          )}
        >
          <div className='mb-3 flex items-center justify-between'>
            <span className='text-xs font-semibold uppercase tracking-widest text-muted-foreground'>
              Apollo
            </span>
            <Drawer.Close
              className='text-muted-foreground hover:text-foreground transition-colors'
              aria-label='Close chat'
            >
              <XIcon className='size-4' />
            </Drawer.Close>
          </div>
          <div className='min-h-0 flex-1'>
            <ChatPanel className='h-full' />
          </div>
        </Drawer.Popup>
      </Drawer.Portal>
    </Drawer.Root>
  )
}
