import { useEffect, useRef, useState } from 'react'
import { Moon, Sun } from 'lucide-react'
import './index.css'
import { SimSection } from '@/components/sim-section'
import { WhatIfPanel } from '@/components/what-if-panel'
import { ChatInput } from '@/components/chat-panel/ChatInput'
import { MessageList } from '@/components/message-bubble'
import { ChatProvider, useChatContext } from '@/hooks/useChatContext'
import { cn } from '@/lib/utils'

function App() {
  const [dark, setDark] = useState(true)
  return (
    <ChatProvider>
      <div
        className={cn(
          'min-h-screen bg-background text-foreground',
          dark && 'dark',
        )}
      >
        <main className='pb-32'>
          <div className='page-container py-6'>
            <AppHeader dark={dark} onToggle={() => setDark((d) => !d)} />
            <SimSection className='mt-6' />
            <div className='mt-8 border-t border-border pt-8'>
              <WhatIfPanel />
            </div>
          </div>
        </main>
        <FloatingChat />
      </div>
    </ChatProvider>
  )
}

function FloatingChat() {
  const { messages, send } = useChatContext()
  const streaming = messages.some((m) => m.streaming)
  const [focused, setFocused] = useState(false)
  const containerRef = useRef<HTMLDivElement>(null)
  const bottomRef = useRef<HTMLDivElement>(null)

  const isExpanded = focused
  const hasMessages = focused && messages.length > 0

  // Collapse only on mousedown outside — Enter key submit never triggers this.
  useEffect(() => {
    function handleMouseDown(e: MouseEvent) {
      if (
        containerRef.current &&
        !containerRef.current.contains(e.target as Node)
      ) {
        setFocused(false)
      }
    }
    document.addEventListener('mousedown', handleMouseDown)
    return () => document.removeEventListener('mousedown', handleMouseDown)
  }, [])

  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: 'smooth' })
  }, [messages])

  return (
    <div
      ref={containerRef}
      className={cn(
        'fixed bottom-10 left-1/2 z-40 -translate-x-1/2',
        'rounded-xl border border-border bg-background/95 shadow-xl backdrop-blur',
        'transition-[width] duration-200',
        isExpanded
          ? 'w-[min(680px,calc(100vw-16px))]'
          : 'w-[min(520px,calc(100vw-16px))]',
      )}
      onFocus={() => setFocused(true)}
    >
      {/* Messages panel — animates in when there are messages */}
      <div
        className={cn(
          'overflow-hidden transition-[max-height] duration-300 ease-in-out',
          hasMessages ? 'max-h-[600px]' : 'max-h-0',
        )}
      >
        <div className='max-h-[600px] overflow-y-auto px-4 pb-2 pt-4'>
          <MessageList messages={messages} />
          <div ref={bottomRef} />
        </div>
        <div className='border-t border-border' />
      </div>

      {/* Input row */}
      <div className='px-4 py-3'>
        <ChatInput onSubmit={send} disabled={streaming} />
      </div>
    </div>
  )
}

function AppHeader({
  className,
  dark,
  onToggle,
}: {
  className?: string
  dark: boolean
  onToggle: () => void
}) {
  return (
    <div className={cn('flex items-start justify-between', className)}>
      <div>
        <p className='text-[10px] font-mono uppercase tracking-widest text-muted-foreground/50'>
          HP Metal Jet S100
        </p>
        <h1 className='text-xl font-semibold tracking-tight text-foreground'>
          Apollo Digital Co-Pilot
        </h1>
      </div>
      <button
        onClick={onToggle}
        className='mt-1 text-muted-foreground hover:text-foreground transition-colors'
        aria-label='Toggle theme'
      >
        {dark ? <Sun size={16} /> : <Moon size={16} />}
      </button>
    </div>
  )
}

export default App
