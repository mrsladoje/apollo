import '@testing-library/jest-dom/vitest'

// jsdom doesn't ship a usable EventSource — stub it for hooks that import it.
class StubEventSource {
  url: string
  readyState = 0
  onmessage: ((ev: MessageEvent) => void) | null = null
  onerror: ((ev: Event) => void) | null = null
  onopen: ((ev: Event) => void) | null = null
  constructor(url: string) {
    this.url = url
  }
  addEventListener() {}
  removeEventListener() {}
  close() {
    this.readyState = 2
  }
}

if (typeof globalThis.EventSource === 'undefined') {
  ;(globalThis as { EventSource: unknown }).EventSource = StubEventSource
}

// jsdom + Recharts: ResizeObserver isn't implemented.
class StubResizeObserver {
  observe() {}
  unobserve() {}
  disconnect() {}
}
if (typeof globalThis.ResizeObserver === 'undefined') {
  ;(globalThis as { ResizeObserver: unknown }).ResizeObserver =
    StubResizeObserver
}

// scrollIntoView smoothness used by the citation-chip click handler.
if (!('scrollIntoView' in HTMLElement.prototype)) {
  ;(HTMLElement.prototype as unknown as { scrollIntoView: () => void }).scrollIntoView = () => {}
}
