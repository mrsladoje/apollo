import { useRef, useEffect, useState } from 'react'
import { motion } from 'framer-motion'
import { Tooltip } from 'react-tooltip'
import { Trash2 } from 'lucide-react'
import { cn } from '@/lib/utils'
import { SimSection } from '@/components/sim-section'
import { WhatIfPanel } from '@/components/what-if-panel'
import { ChatInput } from '@/components/chat-panel/ChatInput'
import { MessageList } from '@/components/message-bubble'
import { useChatContext } from '@/hooks/useChatContext'

const APOLLO_TOOLS: { name: string; blurb: string }[] = [
  {
    name: 'query_historian',
    blurb: 'Pull metric history for one component on a single run.',
  },
  {
    name: 'late_interaction_search',
    blurb:
      'Semantic search across run logs and obituaries to explain why something failed.',
  },
  {
    name: 'compare_runs',
    blurb: 'Diff a metric across multiple runs, side by side.',
  },
  {
    name: 'run_counterfactual',
    blurb:
      'Deepcopy a run, branch at any tick, replay an alternate action — exact, not estimated.',
  },
  {
    name: 'plot_component_history',
    blurb: "Render a component's full timeline for one run.",
  },
]

interface ChatScreenProps {
  className?: string
}

function FixedChat() {
  const { messages, send, clear } = useChatContext()
  const streaming = messages.some((m) => m.streaming)
  const canClear = messages.length > 0 && !streaming
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
    if (messages.length === 0) return
    bottomRef.current?.scrollIntoView({ behavior: 'smooth', block: 'nearest' })
  }, [messages])

  return (
    <div
      ref={containerRef}
      className={cn(
        'fixed z-40',
        'bottom-0 left-0 right-0 rounded-t-2xl',
        'sm:left-1/2 sm:right-auto sm:-translate-x-1/2 sm:bottom-8 sm:rounded-full',
        'transition-[width,border-radius] duration-300 ease-out',
        'w-full',
        focused && hasMessages && 'sm:rounded-3xl',
        focused
          ? 'sm:w-[min(680px,calc(100vw-32px))]'
          : 'sm:w-[min(520px,calc(100vw-32px))]',
      )}
      style={{
        background: 'rgba(255,255,255,0.94)',
        backdropFilter: 'blur(16px) saturate(140%)',
        WebkitBackdropFilter: 'blur(16px) saturate(140%)',
        border: '1px solid rgb(225 230 236)',
        boxShadow:
          '0 1px 0 rgba(255,255,255,1) inset,' +
          '0 12px 36px -16px rgba(15,23,42,0.16),' +
          '0 2px 8px -4px rgba(15,23,42,0.06)',
      }}
      onFocus={() => setFocused(true)}
    >
      <div
        className={cn(
          'overflow-hidden transition-[max-height] duration-400 ease-in-out',
          hasMessages ? 'max-h-[500px]' : 'max-h-0',
        )}
      >
        <div className='hp-scroll relative max-h-[500px] overflow-y-auto px-5 pb-3 pt-5'>
          <MessageList messages={messages} />
          <div ref={bottomRef} />
        </div>
        <div className='hp-divider' />
      </div>

      <div className='flex items-center gap-2 px-5 py-3'>
        <button
          type='button'
          onClick={clear}
          disabled={!canClear}
          aria-label='Clear chat'
          title='Clear chat'
          className={cn(
            'flex h-7 w-7 shrink-0 items-center justify-center rounded-full text-muted-foreground transition-colors',
            'hover:bg-[rgba(15,23,42,0.06)] hover:text-foreground',
            'disabled:cursor-not-allowed disabled:opacity-30 disabled:hover:bg-transparent disabled:hover:text-muted-foreground',
          )}
        >
          <Trash2 className='h-3.5 w-3.5' strokeWidth={2} />
        </button>
        <ChatInput
          className='flex-1'
          onSubmit={send}
          disabled={streaming}
        />
      </div>
    </div>
  )
}

export function ChatScreen({ className }: ChatScreenProps) {
  useEffect(() => {
    window.scrollTo(0, 0)
  }, [])

  return (
    <motion.div
      className={cn('relative min-h-screen pb-32 text-foreground', className)}
      initial={{ opacity: 0, y: 32 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ duration: 0.55, ease: [0.4, 0, 0.2, 1] }}
    >
      <header className='page-container pt-10 pb-8'>
        <motion.div
          className='flex items-center justify-between gap-6'
          initial={{ opacity: 0, y: 12 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ duration: 0.5, delay: 0.1, ease: 'easeOut' }}
        >
          <div className='flex items-center gap-3'>
            <span
              aria-hidden
              className='inline-block h-2.5 w-2.5 rounded-full'
              style={{
                background: '#0096D6',
                boxShadow: '0 0 0 3px rgba(0,150,214,0.18)',
              }}
            />
            <span
              className='font-sans text-[11px] font-semibold uppercase tracking-[0.28em]'
              style={{ color: '#1A1F2C' }}
            >
              Apollo
            </span>
            <span className='h-3 w-px bg-[rgba(15,23,42,0.16)]' />
            <span className='font-sans text-[10px] font-medium uppercase tracking-[0.28em] text-muted-foreground'>
              HP Metal Jet S100
            </span>
          </div>

          <span className='hidden font-mono text-[10px] uppercase tracking-[0.28em] text-muted-foreground/65 sm:block'>
            Predictive maintenance
          </span>
        </motion.div>

        <motion.h1
          className='mt-8 max-w-[660px] font-display leading-[1.08] tracking-[-0.022em] text-[#1A1F2C]'
          style={{
            fontSize: 'clamp(28px, 3.4vw, 42px)',
            fontWeight: 500,
          }}
          initial={{ opacity: 0, y: 12 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ duration: 0.55, delay: 0.18, ease: 'easeOut' }}
        >
          <span
            data-tooltip-id='apollo-tools'
            tabIndex={0}
            aria-describedby='apollo-tools'
            style={{
              fontWeight: 600,
              color: '#0096D6',
              cursor: 'help',
              borderBottom: '1px dotted rgba(0,150,214,0.45)',
              outline: 'none',
            }}
          >
            Five tools.
          </span>{' '}
          One printer. Every tick on the record.
        </motion.h1>
      </header>

      <Tooltip
        id='apollo-tools'
        className='apollo-tooltip'
        classNameArrow='apollo-tooltip-arrow'
        place='bottom-start'
        offset={10}
        opacity={1}
        clickable
        delayShow={200}
        delayHide={120}
      >
        <div className='apollo-tooltip-inner'>
          <div className='apollo-tooltip-eyebrow'>Apollo · Tool calls</div>
          <ul className='apollo-tooltip-list'>
            {APOLLO_TOOLS.map((tool) => (
              <li key={tool.name}>
                <code>{tool.name}</code>
                <span>{tool.blurb}</span>
              </li>
            ))}
          </ul>
        </div>
      </Tooltip>

      <div className='page-container space-y-10'>
        <motion.div
          initial={{ opacity: 0, y: 16 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ duration: 0.5, delay: 0.26, ease: 'easeOut' }}
        >
          <SimSection />
        </motion.div>

        <motion.div
          className='relative pt-10'
          initial={{ opacity: 0, y: 16 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ duration: 0.5, delay: 0.36, ease: 'easeOut' }}
        >
          <span className='hp-divider absolute inset-x-0 top-0' />
          <WhatIfPanel />
        </motion.div>
      </div>

      <FixedChat />
    </motion.div>
  )
}
