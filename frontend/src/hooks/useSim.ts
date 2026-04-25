import { useEffect, useMemo, useReducer } from 'react'
import type {
  SimEvent,
  ComponentState,
  Forecast,
  FailureEvent,
  ObitEvent,
  UniverseId,
  ComponentId,
} from '@/types'

interface UniverseState {
  universe: UniverseId
  t: number
  states: Record<ComponentId, ComponentState>
  forecasts: Record<ComponentId, Forecast>
  failures: FailureEvent[]
  obituaries: ObitEvent[]
  history: Array<{ t: number; health: number }>
}

type SimState = Record<UniverseId, UniverseState>

const UNIVERSES: UniverseId[] = ['dark-twin', 'fixed-schedule', 'apollo']

function initialState(): SimState {
  const blank = (u: UniverseId): UniverseState => ({
    universe: u,
    t: 0,
    states: {} as Record<ComponentId, ComponentState>,
    forecasts: {} as Record<ComponentId, Forecast>,
    failures: [],
    obituaries: [],
    history: [],
  })
  return {
    'dark-twin': blank('dark-twin'),
    'fixed-schedule': blank('fixed-schedule'),
    apollo: blank('apollo'),
  }
}

function avgHealth(states: Record<ComponentId, ComponentState>): number {
  const vals = Object.values(states).map((s) => s.health)
  return vals.length === 0 ? 1 : vals.reduce((a, b) => a + b, 0) / vals.length
}

function simReducer(state: SimState, event: SimEvent): SimState {
  const u = event.universe as UniverseId
  const prev = state[u]

  switch (event.type) {
    case 'tick': {
      const newStates = { ...prev.states }
      for (const s of event.states) {
        newStates[s.component_id] = s
      }
      const avg = avgHealth(newStates)
      return {
        ...state,
        [u]: {
          ...prev,
          t: event.t,
          states: newStates,
          history: [...prev.history, { t: event.t, health: avg }],
        },
      }
    }
    case 'forecast':
      return {
        ...state,
        [u]: {
          ...prev,
          forecasts: { ...prev.forecasts, [event.component]: event.band },
        },
      }
    case 'failure':
      return {
        ...state,
        [u]: { ...prev, failures: [...prev.failures, event] },
      }
    case 'obituary':
      return {
        ...state,
        [u]: { ...prev, obituaries: [...prev.obituaries, event] },
      }
    default:
      return state
  }
}

export function useSim() {
  const [state, dispatch] = useReducer(simReducer, undefined, initialState)

  useEffect(() => {
    const sources = UNIVERSES.map((u) => {
      const es = new EventSource(`/api/sim/stream/${u}`)
      es.addEventListener('message', (e) => {
        try {
          const event: SimEvent = JSON.parse(e.data)
          dispatch(event)
        } catch {
          // ignore
        }
      })
      return es
    })

    return () => sources.forEach((es) => es.close())
  }, [])

  const masterHealth = useMemo(() => {
    return {
      'dark-twin': state['dark-twin'].history,
      'fixed-schedule': state['fixed-schedule'].history,
      apollo: state['apollo'].history,
    }
  }, [state])

  return { state, masterHealth }
}
