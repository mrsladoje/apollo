import { motion } from 'framer-motion'
import { ApolloLogo } from './ApolloLogo'
import { PrinterCanvas } from './PrinterCanvas'

interface LandingScreenProps {
  onAsk: () => void
}

// CTA fades in after the logo color animation completes (~4.5s)
const CTA_DELAY = 4.6

export function LandingScreen({ onAsk }: LandingScreenProps) {
  return (
    <motion.div
      style={{
        position: 'fixed',
        inset: 0,
        zIndex: 50,
        background: 'white',
        overflow: 'hidden',
      }}
      initial={{ opacity: 1 }}
      exit={{ opacity: 0, y: -40 }}
      transition={{ duration: 0.7, ease: [0.4, 0, 0.2, 1] }}
    >
      {/* APOLLO watermark — absolute, full width, vertically centered, behind everything */}
      <div
        style={{
          position: 'absolute',
          left: 0,
          right: 0,
          top: '50%',
          transform: 'translateY(-50%)',
          pointerEvents: 'none',
          zIndex: 0,
        }}
      >
        <ApolloLogo style={{ width: '100%', display: 'block' }} />
      </div>

      {/* 3D printer model — 1024×722px centered, 50% opacity (matches Figma newnow 2) */}
      <div
        style={{
          position: 'absolute',
          left: '50%',
          top: '50%',
          transform: 'translate(-50%, -50%)',
          width: 'min(1024px, 100%)',
          aspectRatio: '1024 / 722',
          pointerEvents: 'none',
          zIndex: 10,
        }}
      >
        <PrinterCanvas
          className='absolute inset-0 w-full h-full'
          wrapperOpacity={0.5}
        />
      </div>

      {/* Headline — Figma: top calc(50% - 41px), left calc(50% - 568px), 64px Lora Bold */}
      <motion.p
        style={{
          position: 'absolute',
          top: 'calc(50% - 41px)',
          left: 'calc(50% - 568px)',
          fontSize: '64px',
          fontFamily: '"Lora", serif',
          fontWeight: 700,
          lineHeight: 'normal',
          whiteSpace: 'nowrap',
          margin: 0,
          zIndex: 20,
          color: '#000000',
        }}
        initial={{ opacity: 0, y: 20 }}
        animate={{ opacity: 1, y: 0 }}
        transition={{ duration: 0.8, delay: CTA_DELAY, ease: 'easeOut' }}
      >
        Not sure what&apos;s wrong? Ask{' '}
        <span
          style={{
            fontFamily: '"Inter", sans-serif',
            fontWeight: 700,
            color: '#2563eb',
          }}
        >
          Apollo.
        </span>
      </motion.p>

      {/* Ask button — Figma: centered, top calc(50% + 102.5px), 64px×16px padding */}
      <motion.div
        style={{
          position: 'absolute',
          left: '50%',
          top: 'calc(50% + 102.5px)',
          x: '-50%',
          zIndex: 20,
        }}
        initial={{ opacity: 0, y: 20 }}
        animate={{ opacity: 1, y: 0 }}
        transition={{ duration: 0.8, delay: CTA_DELAY, ease: 'easeOut' }}
      >
        <motion.button
          onClick={onAsk}
          style={{
            display: 'flex',
            alignItems: 'center',
            justifyContent: 'center',
            padding: '16px 64px',
            fontSize: '16px',
            fontWeight: 500,
            fontFamily: '"Inter", sans-serif',
            background: '#2563eb',
            color: 'white',
            border: 'none',
            cursor: 'pointer',
            boxShadow: '0px 0px 8px 0px rgba(0,0,0,0.08)',
            whiteSpace: 'nowrap',
          }}
          whileHover={{ scale: 1.03, background: '#1d4ed8' }}
          whileTap={{ scale: 0.97 }}
          transition={{ type: 'spring', stiffness: 400, damping: 20 }}
        >
          Ask.
        </motion.button>
      </motion.div>
    </motion.div>
  )
}
