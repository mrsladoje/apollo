import { useEffect, useState } from 'react'
import { motion, AnimatePresence } from 'framer-motion'
import { ApolloLogo } from './ApolloLogo'
import { PrinterCanvas } from './PrinterCanvas'

interface LandingScreenProps {
  onAsk: () => void
}

const ASCII_FADE_OUT_AT = 1800
const HEADLINE_DELAY = 3.1

export function LandingScreen({ onAsk }: LandingScreenProps) {
  const [logoVisible, setLogoVisible] = useState(true)

  useEffect(() => {
    const t = setTimeout(() => setLogoVisible(false), ASCII_FADE_OUT_AT)
    return () => clearTimeout(t)
  }, [])

  return (
    <motion.div
      style={{
        position: 'fixed',
        inset: 0,
        zIndex: 50,
        overflow: 'hidden',
        background:
          'radial-gradient(ellipse 70% 60% at 95% -5%, rgba(0,150,214,0.10), transparent 55%),' +
          'radial-gradient(ellipse 60% 60% at 5% 105%, rgba(0,150,214,0.07), transparent 55%),' +
          '#ffffff',
        fontFamily: '"Inter", system-ui, sans-serif',
      }}
      initial={{ opacity: 1 }}
      exit={{ opacity: 0 }}
      transition={{ duration: 0.5, ease: [0.4, 0, 0.2, 1] }}
    >
      {/* Top-left identity bar */}
      <motion.div
        style={{
          position: 'absolute',
          top: 28,
          left: 32,
          display: 'flex',
          alignItems: 'center',
          gap: 12,
          zIndex: 30,
        }}
        initial={{ opacity: 0, y: -6 }}
        animate={{ opacity: 1, y: 0 }}
        transition={{ duration: 0.6, delay: 0.2, ease: 'easeOut' }}
      >
        <span
          aria-hidden
          style={{
            display: 'inline-block',
            width: 9,
            height: 9,
            borderRadius: '50%',
            background: '#0096D6',
            boxShadow: '0 0 0 3px rgba(0,150,214,0.18)',
          }}
        />
        <span
          style={{
            fontSize: 11,
            fontWeight: 600,
            letterSpacing: '0.28em',
            textTransform: 'uppercase',
            color: '#1A1F2C',
          }}
        >
          Apollo
        </span>
        <span
          aria-hidden
          style={{ width: 1, height: 12, background: 'rgba(15,23,42,0.16)' }}
        />
        <span
          style={{
            fontSize: 10,
            fontWeight: 500,
            letterSpacing: '0.28em',
            textTransform: 'uppercase',
            color: 'rgba(26,31,44,0.55)',
          }}
        >
          HP&nbsp;Metal&nbsp;Jet&nbsp;S100
        </span>
      </motion.div>

      {/* Top-right meta */}
      <motion.div
        style={{
          position: 'absolute',
          top: 28,
          right: 32,
          display: 'flex',
          alignItems: 'center',
          gap: 12,
          zIndex: 30,
          fontFamily: '"IBM Plex Mono", monospace',
          fontSize: 10,
          letterSpacing: '0.16em',
          textTransform: 'uppercase',
          color: 'rgba(26,31,44,0.5)',
        }}
        initial={{ opacity: 0 }}
        animate={{ opacity: 1 }}
        transition={{ duration: 0.6, delay: 0.3, ease: 'easeOut' }}
      >
        <span>v1.0</span>
        <span style={{ width: 1, height: 10, background: 'rgba(15,23,42,0.16)' }} />
        <span style={{ display: 'flex', alignItems: 'center', gap: 6 }}>
          <span
            style={{
              display: 'inline-block',
              width: 6,
              height: 6,
              borderRadius: '50%',
              background: '#16A34A',
              boxShadow: '0 0 6px rgba(22,163,74,0.55)',
            }}
          />
          Ready
        </span>
      </motion.div>

      {/* Hero stage */}
      <div
        style={{
          position: 'absolute',
          inset: 0,
          display: 'flex',
          alignItems: 'center',
          justifyContent: 'center',
        }}
      >
        {/* ASCII art APOLLO — fades out as printer takes the stage */}
        <AnimatePresence>
          {logoVisible && (
            <motion.div
              key='ascii'
              style={{
                position: 'absolute',
                inset: 0,
                display: 'flex',
                alignItems: 'center',
                justifyContent: 'center',
                pointerEvents: 'none',
                zIndex: 5,
              }}
              initial={{ opacity: 1 }}
              exit={{ opacity: 0, scale: 0.985, filter: 'blur(4px)' }}
              transition={{ duration: 0.85, ease: [0.4, 0, 0.2, 1] }}
            >
              <ApolloLogo />
            </motion.div>
          )}
        </AnimatePresence>

        {/* 3D printer model — stable wrapper handles centering, motion child animates */}
        <div
          style={{
            position: 'absolute',
            left: '50%',
            top: '50%',
            transform: 'translate(-50%, -50%)',
            width: 'min(960px, 100%)',
            aspectRatio: '1024 / 722',
            pointerEvents: 'none',
            zIndex: 10,
          }}
        >
          <motion.div
            style={{ width: '100%', height: '100%' }}
            initial={{ opacity: 0, scale: 0.96 }}
            animate={{ opacity: 1, scale: 1 }}
            transition={{
              duration: 1.2,
              delay: 1.9,
              ease: [0.22, 0.61, 0.36, 1],
            }}
          >
            <PrinterCanvas
              className='absolute inset-0 w-full h-full'
              wrapperOpacity={1}
            />
          </motion.div>
        </div>
      </div>

      {/* Headline + CTA */}
      <motion.div
        style={{
          position: 'absolute',
          left: 0,
          right: 0,
          bottom: 'clamp(48px, 11vh, 96px)',
          display: 'flex',
          flexDirection: 'column',
          alignItems: 'center',
          gap: 24,
          padding: '0 24px',
          zIndex: 20,
        }}
        initial={{ opacity: 0, y: 16 }}
        animate={{ opacity: 1, y: 0 }}
        transition={{
          duration: 0.85,
          delay: HEADLINE_DELAY,
          ease: [0.22, 0.61, 0.36, 1],
        }}
      >
        <p
          style={{
            fontFamily: '"Inter", system-ui, sans-serif',
            fontWeight: 500,
            fontSize: 'clamp(26px, 3.4vw, 40px)',
            lineHeight: 1.1,
            letterSpacing: '-0.022em',
            color: '#1A1F2C',
            textAlign: 'center',
            margin: 0,
          }}
        >
          Not sure what&apos;s wrong?{' '}
          <span style={{ fontWeight: 600, color: '#0096D6' }}>
            Ask&nbsp;Apollo.
          </span>
        </p>

        <motion.button
          onClick={onAsk}
          className='hp-focus-ring'
          style={{
            position: 'relative',
            display: 'inline-flex',
            alignItems: 'center',
            justifyContent: 'center',
            gap: 12,
            padding: '13px 36px',
            fontSize: 12,
            fontWeight: 600,
            letterSpacing: '0.18em',
            textTransform: 'uppercase',
            fontFamily: '"Inter", system-ui, sans-serif',
            color: '#FFFFFF',
            background: 'linear-gradient(180deg, #0096D6 0%, #0073A8 100%)',
            border: '1px solid rgba(0,115,168,0.9)',
            cursor: 'pointer',
            borderRadius: 999,
            boxShadow:
              '0 1px 0 rgba(255,255,255,0.2) inset,' +
              '0 8px 22px -8px rgba(0,150,214,0.55)',
            whiteSpace: 'nowrap',
          }}
          whileHover={{
            scale: 1.02,
            boxShadow:
              '0 1px 0 rgba(255,255,255,0.25) inset,' +
              '0 14px 28px -8px rgba(0,150,214,0.65),' +
              '0 0 0 4px rgba(0,150,214,0.18)',
          }}
          whileTap={{ scale: 0.98 }}
          transition={{ type: 'spring', stiffness: 380, damping: 24 }}
        >
          <span style={{ position: 'relative', zIndex: 1 }}>Begin diagnosis</span>
          <span
            aria-hidden
            style={{
              position: 'relative',
              zIndex: 1,
              display: 'inline-flex',
              alignItems: 'center',
              justifyContent: 'center',
              width: 18,
              height: 18,
              borderRadius: 999,
              background: '#FFFFFF',
              color: '#0096D6',
              fontSize: 12,
              fontWeight: 700,
              transform: 'translateY(-0.5px)',
              boxShadow: '0 1px 0 rgba(0,0,0,0.05)',
            }}
          >
            →
          </span>
        </motion.button>
      </motion.div>
    </motion.div>
  )
}
