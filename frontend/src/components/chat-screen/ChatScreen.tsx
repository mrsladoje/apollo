import { useRef, useEffect, useState } from 'react'
import { motion } from 'framer-motion'
import { cn } from '@/lib/utils'
import { SimSection } from '@/components/sim-section'
import { WhatIfPanel } from '@/components/what-if-panel'
import { ChatInput } from '@/components/chat-panel/ChatInput'
import { MessageList } from '@/components/message-bubble'
import { useChatContext } from '@/hooks/useChatContext'

interface ChatScreenProps {
  className?: string
}

function FixedChat() {
  const { messages, send } = useChatContext()
  const streaming = messages.some((m) => m.streaming)
  const [focused, setFocused] = useState(false)
  const containerRef = useRef<HTMLDivElement>(null)
  const bottomRef = useRef<HTMLDivElement>(null)

  const hasMessages = focused && messages.length > 0

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
        'fixed z-40 bg-background/95 backdrop-blur shadow-xl',
        // Mobile: full width, flush to bottom, top border only
        'bottom-0 left-0 right-0 border-t border-border',
        // Desktop: 40px from bottom, centered, left+right+top borders, no bottom border
        'sm:left-1/2 sm:right-auto sm:-translate-x-1/2 sm:bottom-10 sm:border sm:border-b-0',
        'transition-[width] duration-200',
        // Width: full on mobile, constrained on desktop
        'w-full',
        focused
          ? 'sm:w-[min(680px,calc(100vw-32px))]'
          : 'sm:w-[min(520px,calc(100vw-32px))]',
      )}
      onFocus={() => setFocused(true)}
    >
      {/* Messages panel */}
      <div
        className={cn(
          'overflow-hidden transition-[max-height] duration-300 ease-in-out',
          hasMessages ? 'max-h-[500px]' : 'max-h-0',
        )}
      >
        <div className='max-h-[500px] overflow-y-auto px-4 pb-2 pt-4'>
          <MessageList messages={messages} />
          <div ref={bottomRef} />
        </div>
        <div className='border-t border-border' />
      </div>

      {/* Input */}
      <div className='px-4 py-3'>
        <ChatInput onSubmit={send} disabled={streaming} />
      </div>
    </div>
  )
}

export function ChatScreen({ className }: ChatScreenProps) {
  return (
    <motion.div
      className={cn(
        'min-h-screen bg-background text-foreground pb-24',
        className,
      )}
      initial={{ opacity: 0, y: 60 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ duration: 0.6, ease: [0.4, 0, 0.2, 1] }}
    >
      <div className='page-container py-8 space-y-8'>
        {/* Charts section */}
        <motion.div
          initial={{ opacity: 0, y: 20 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ duration: 0.5, delay: 0.15, ease: 'easeOut' }}
        >
          <SimSection />
        </motion.div>

        {/* What-if panel */}
        <motion.div
          className='border-t border-border pt-8'
          initial={{ opacity: 0, y: 20 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ duration: 0.5, delay: 0.25, ease: 'easeOut' }}
        >
          <WhatIfPanel />
        </motion.div>
      </div>

      {/* Fixed chat bar at bottom — same as original but no rounded corners */}
      <FixedChat />
    </motion.div>
  )
}
