import { motion } from 'framer-motion'
import React from 'react'

// ASCII art lifted from scripts/run_dev.sh — sun + APOLLO + dev-stack tagline.
// Each row is decomposed into colored segments matching the bash colorisation,
// remapped to the pearl palette: champagne/rose-gold sun, iridescent rose →
// mauve → violet APOLLO, muted pearl-grey decoration.

type Tone =
  | 'star'
  | 'sun'
  | 'sunCore'
  | 'dim'
  | 'apolloA'
  | 'apolloB'
  | 'apolloC'

interface Segment {
  text: string
  tone: Tone
}

const TONES: Record<Tone, string> = {
  // muted steel — sky stars
  star: '#7AA3BF',
  // HP Blue — sun outline
  sun: '#0096D6',
  // brighter HP cyan — sun core
  sunCore: '#5BB8E0',
  // cool slate — decoration / tagline
  dim: '#94A3B8',
  // APOLLO — graduated HP blue: light → brand → deep
  apolloA: '#33A8DD',
  apolloB: '#0096D6',
  apolloC: '#0073A8',
}

const ROWS: Segment[][] = [
  [{ text: '                    .                      .', tone: 'star' }],
  [
    {
      text: '         .            *        .       .         .       *',
      tone: 'star',
    },
  ],
  [
    {
      text: '    *          .            .                .',
      tone: 'star',
    },
  ],
  [{ text: '                          ___', tone: 'sun' }],
  [
    { text: "                       .-´   `-.", tone: 'sun' },
    { text: '        .    *', tone: 'dim' },
  ],
  [
    { text: '                      /  ', tone: 'sun' },
    { text: '.-~-.', tone: 'sunCore' },
    { text: '  \\', tone: 'sun' },
    { text: '    .', tone: 'dim' },
  ],
  [
    { text: '              .', tone: 'dim' },
    { text: '      |  ', tone: 'sun' },
    { text: '/     \\', tone: 'sunCore' },
    { text: '  |', tone: 'sun' },
    { text: '     *', tone: 'dim' },
  ],
  [
    { text: '                     |  ', tone: 'sun' },
    { text: '\\     /', tone: 'sunCore' },
    { text: '  |', tone: 'sun' },
  ],
  [
    { text: '                      \\  ', tone: 'sun' },
    { text: "'-~-'", tone: 'sunCore' },
    { text: '  /', tone: 'sun' },
    { text: '     .', tone: 'dim' },
  ],
  [{ text: "                       '-.___.-'", tone: 'sun' }],
  [
    {
      text: '        .          *               .           .',
      tone: 'dim',
    },
  ],
  [
    {
      text: '     ___    ____   ___   _      _      ___',
      tone: 'apolloA',
    },
  ],
  [
    {
      text: '    / _ \\  |  _ \\ / _ \\ | |    | |    / _ \\',
      tone: 'apolloA',
    },
  ],
  [
    {
      text: '   | |_| | | |_) | | | || |    | |   | | | |',
      tone: 'apolloB',
    },
  ],
  [
    {
      text: '   |  _  | |  __/| |_| || |___ | |___| |_| |',
      tone: 'apolloB',
    },
  ],
  [
    {
      text: '   |_| |_| |_|    \\___/ |_____||_____|\\___/',
      tone: 'apolloC',
    },
  ],
  [
    {
      text: '        ~ integrated dev stack — backend + frontend ~',
      tone: 'dim',
    },
  ],
]

interface ApolloLogoProps {
  className?: string
  style?: React.CSSProperties
}

export function ApolloLogo({ className, style }: ApolloLogoProps) {
  return (
    <motion.div
      className={className}
      style={{
        position: 'relative',
        display: 'flex',
        flexDirection: 'column',
        alignItems: 'center',
        justifyContent: 'center',
        ...style,
      }}
      initial={{ opacity: 0 }}
      animate={{ opacity: 1 }}
      transition={{ duration: 0.5, ease: 'easeOut' }}
      aria-label='Apollo'
    >
      <pre
        style={{
          margin: 0,
          padding: 0,
          fontFamily: '"IBM Plex Mono", ui-monospace, monospace',
          fontSize: 'clamp(7px, 1.05vw, 14px)',
          lineHeight: 1.08,
          letterSpacing: '0.01em',
          fontWeight: 500,
          textShadow:
            '0 1px 0 rgba(255,255,255,0.9), 0 0 22px rgba(0,150,214,0.18)',
          whiteSpace: 'pre',
          userSelect: 'none',
          position: 'relative',
        }}
      >
        {ROWS.map((row, i) => (
          <motion.div
            key={i}
            style={{ display: 'block' }}
            initial={{ opacity: 0, y: 4, filter: 'blur(2px)' }}
            animate={{ opacity: 1, y: 0, filter: 'blur(0px)' }}
            transition={{
              duration: 0.45,
              delay: 0.05 + i * 0.028,
              ease: [0.22, 0.61, 0.36, 1],
            }}
          >
            {row.map((seg, j) => (
              <span key={j} style={{ color: TONES[seg.tone] }}>
                {seg.text}
              </span>
            ))}
          </motion.div>
        ))}

        {/* Pearl shimmer sweep — single elegant pass after reveal */}
        <motion.span
          aria-hidden
          style={{
            position: 'absolute',
            inset: 0,
            pointerEvents: 'none',
            background:
              'linear-gradient(110deg, transparent 38%, rgba(255,255,255,0.55) 50%, transparent 62%)',
            backgroundSize: '220% 100%',
            mixBlendMode: 'overlay',
          }}
          initial={{ backgroundPosition: '220% 0%', opacity: 0 }}
          animate={{
            backgroundPosition: ['220% 0%', '-120% 0%'],
            opacity: [0, 1, 1, 0],
          }}
          transition={{
            duration: 1.6,
            delay: 0.85,
            times: [0, 0.15, 0.85, 1],
            ease: [0.4, 0, 0.2, 1],
          }}
        />
      </pre>
    </motion.div>
  )
}
