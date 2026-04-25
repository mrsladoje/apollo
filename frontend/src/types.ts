// Frozen SSE event schema (ADR-017, Plan C §3.3)

export type ComponentId =
  | 'blade'
  | 'motor'
  | 'nozzle'
  | 'resistor'
  | 'heater'
  | 'insulation'

export type ComponentStatus = 'FUNCTIONAL' | 'DEGRADED' | 'CRITICAL' | 'FAILED'

export type Severity = 'INFO' | 'WARNING' | 'CRITICAL' | 'REFUSAL'

export type UniverseId = 'dark-twin' | 'fixed-schedule' | 'apollo'

export interface ComponentState {
  component_id: ComponentId
  health: number // 0..1
  status: ComponentStatus
  metrics: Record<string, number>
}

export interface Forecast {
  component_id: ComponentId
  horizon_min: number
  point: number
  lower: number
  upper: number
  ci_level: number
}

export interface Citation {
  run_id: string
  component: ComponentId
  timestamp: string // ISO datetime
}

export interface ToolCall {
  tool:
    | 'query_historian'
    | 'late_interaction_search'
    | 'compare_runs'
    | 'run_counterfactual'
    | 'plot_component_history'
  args: Record<string, unknown>
  result: Record<string, unknown> | null
  call_id: string
  started_at: string
  finished_at: string | null
}

// SSE event discriminated union
export type SSEEvent =
  | { type: 'text-delta'; payload: { token: string } }
  | {
      type: 'tool-call-start'
      payload: { tool: string; args: object; call_id: string }
    }
  | { type: 'tool-result'; payload: { call_id: string; result: object } }
  | { type: 'citation'; payload: Citation }
  | { type: 'done'; payload: { trace_url: string } }

export interface Message {
  id: string
  role: 'user' | 'apollo'
  text: string
  severity?: Severity
  citations: Citation[]
  tool_calls: ToolCall[]
  trace_url?: string
  streaming: boolean
}

export interface SimTick {
  run_id: string
  universe: UniverseId
  t: number
  states: ComponentState[]
}

export interface ForecastTick {
  run_id: string
  universe: UniverseId
  t: number
  component: ComponentId
  band: Forecast
}

export interface FailureEvent {
  run_id: string
  universe: UniverseId
  component: ComponentId
  t_fail: number
}

export interface ObitEvent {
  run_id: string
  universe: UniverseId
  component: ComponentId
  narrative: string
  citations: Citation[]
}

export type SimEvent =
  | ({ type: 'tick' } & SimTick)
  | ({ type: 'forecast' } & ForecastTick)
  | ({ type: 'failure' } & FailureEvent)
  | ({ type: 'obituary' } & ObitEvent)

export interface CounterfactualResult {
  run_id: string
  branch_t: number
  alt_action: string
  original_health: Array<{ t: number; health: number }>
  alt_health: Array<{ t: number; health: number }>
  uptime_delta_h: number
}

export const COMPONENTS: ComponentId[] = [
  'blade',
  'motor',
  'nozzle',
  'resistor',
  'heater',
  'insulation',
]

export const UNIVERSES: Array<{ id: UniverseId; label: string }> = [
  { id: 'dark-twin', label: 'Universe A — Dark Twin' },
  { id: 'fixed-schedule', label: 'Universe B — Fixed Schedule' },
  { id: 'apollo', label: 'Universe C — Apollo (AI)' },
]
