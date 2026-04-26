import type { FC } from 'react'
import { Tooltip } from 'react-tooltip'
import { cn } from '@/lib/utils'
import type { UniverseId } from '@/types'

interface IconProps {
  size?: number
}

function DevilIcon({ size = 13 }: IconProps) {
  return (
    <svg
      width={size}
      height={size}
      viewBox='0 0 24 24'
      fill='none'
      stroke='currentColor'
      strokeWidth='1.7'
      strokeLinecap='round'
      strokeLinejoin='round'
      aria-hidden
    >
      <path d='M7 7 L8 3 L10 7' />
      <path d='M17 7 L16 3 L14 7' />
      <path d='M5 13 A7 7 0 0 1 19 13 A7 7 0 0 1 12 20 A7 7 0 0 1 5 13 Z' />
      <path d='M9 12 L10.5 13' />
      <path d='M15 12 L13.5 13' />
      <path d='M9 16 Q12 14 15 16' />
    </svg>
  )
}

function WrenchIcon({ size = 13 }: IconProps) {
  return (
    <svg
      width={size}
      height={size}
      viewBox='0 0 24 24'
      fill='none'
      stroke='currentColor'
      strokeWidth='1.7'
      strokeLinecap='round'
      strokeLinejoin='round'
      aria-hidden
    >
      <path d='M14.7 6.3 a1 1 0 0 0 0 1.4 l1.6 1.6 a1 1 0 0 0 1.4 0 l3.77 -3.77 a6 6 0 0 1 -7.94 7.94 l-6.91 6.91 a2.12 2.12 0 0 1 -3 -3 l6.91 -6.91 a6 6 0 0 1 7.94 -7.94 l-3.76 3.76 z' />
    </svg>
  )
}

function RobotIcon({ size = 13 }: IconProps) {
  return (
    <svg
      width={size}
      height={size}
      viewBox='0 0 24 24'
      fill='none'
      stroke='currentColor'
      strokeWidth='1.7'
      strokeLinecap='round'
      strokeLinejoin='round'
      aria-hidden
    >
      <path d='M12 8 V4 H8' />
      <circle cx='8' cy='4' r='0.8' fill='currentColor' stroke='none' />
      <rect x='4' y='8' width='16' height='12' rx='2.5' />
      <path d='M2 14 V16' />
      <path d='M22 14 V16' />
      <circle cx='9.2' cy='13.5' r='1.2' />
      <circle cx='14.8' cy='13.5' r='1.2' />
      <path d='M9.5 17.5 H14.5' />
    </svg>
  )
}

interface UniverseMeta {
  accent: string
  badgeBg: string
  badgeBorder: string
  badgeColor: string
  labelColor: string
  tooltipTitle: string
  tooltipBody: string
  Icon: FC<IconProps>
}

const UNIVERSE_META: Record<UniverseId, UniverseMeta> = {
  'dark-twin': {
    accent: '#B91C1C',
    badgeBg: 'rgba(185, 28, 28, 0.08)',
    badgeBorder: 'rgba(185, 28, 28, 0.22)',
    badgeColor: '#B91C1C',
    labelColor: '#B91C1C',
    tooltipTitle: 'Dark Twin · Control',
    tooltipBody:
      'A no-maintenance shadow of the printer. Components run until they die — never repaired, never replaced. Apollo uses it as ground truth to measure how much downtime smarter policies actually prevent.',
    Icon: DevilIcon,
  },
  'fixed-schedule': {
    accent: '#B45309',
    badgeBg: 'rgba(180, 83, 9, 0.08)',
    badgeBorder: 'rgba(180, 83, 9, 0.22)',
    badgeColor: '#B45309',
    labelColor: '#1A1F2C',
    tooltipTitle: 'Fixed Schedule · Calendar maintenance',
    tooltipBody:
      'Old-school preventive maintenance. Parts are swapped on a fixed cadence regardless of their condition — catching some failures, but burning through plenty of healthy components in the process.',
    Icon: WrenchIcon,
  },
  apollo: {
    accent: '#0096D6',
    badgeBg: 'rgba(0, 150, 214, 0.10)',
    badgeBorder: 'rgba(0, 150, 214, 0.28)',
    badgeColor: '#0096D6',
    labelColor: '#0073A8',
    tooltipTitle: 'Apollo · AI co-pilot',
    tooltipBody:
      "Reads live telemetry, forecasts each component's health curve, and proposes maintenance only when the data justifies it — every recommendation grounded in citations back to the run log.",
    Icon: RobotIcon,
  },
}

interface UniverseHeaderProps {
  universeId: UniverseId
  label: string
  t: number
  className?: string
}

export function UniverseHeader({
  universeId,
  label,
  t,
  className,
}: UniverseHeaderProps) {
  const meta = UNIVERSE_META[universeId]
  const tooltipId = `universe-tip-${universeId}`
  const Icon = meta.Icon

  return (
    <div
      className={cn('flex items-center justify-between gap-2', className)}
    >
      <div
        data-tooltip-id={tooltipId}
        tabIndex={0}
        aria-describedby={tooltipId}
        className='group inline-flex min-w-0 items-center gap-2 rounded-md outline-none focus-visible:ring-2 focus-visible:ring-[#0096D6]/40'
        style={{ cursor: 'help' }}
      >
        <span
          aria-hidden
          className='inline-flex shrink-0 items-center justify-center transition-transform duration-200 group-hover:scale-[1.08]'
          style={{
            width: 22,
            height: 22,
            borderRadius: 6,
            background: meta.badgeBg,
            border: `1px solid ${meta.badgeBorder}`,
            color: meta.badgeColor,
            boxShadow: '0 1px 0 rgba(255,255,255,0.9) inset',
          }}
        >
          <Icon size={13} />
        </span>
        <p
          className='truncate text-[12px] font-semibold tracking-tight'
          style={{ color: meta.labelColor }}
        >
          {label}
        </p>
      </div>

      <span className='font-mono text-[10px] tabular-nums text-muted-foreground/60'>
        t={t}
      </span>

      <Tooltip
        id={tooltipId}
        className='apollo-tooltip'
        classNameArrow='apollo-tooltip-arrow'
        place='bottom-start'
        offset={10}
        opacity={1}
        clickable
        delayShow={180}
        delayHide={120}
      >
        <div className='apollo-tooltip-inner' style={{ maxWidth: 280 }}>
          <div
            className='apollo-tooltip-eyebrow'
            style={{
              color: meta.accent,
              borderBottomColor: `${meta.accent}29`,
            }}
          >
            {meta.tooltipTitle}
          </div>
          <div
            style={{
              fontSize: 12,
              lineHeight: 1.5,
              color: 'rgba(26, 31, 44, 0.78)',
            }}
          >
            {meta.tooltipBody}
          </div>
        </div>
      </Tooltip>
    </div>
  )
}
