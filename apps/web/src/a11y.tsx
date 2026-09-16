// Display preferences (PRD FR-06): contrast, zoom, and motion. They persist for the learner
// and are applied as attributes and a CSS variable on <html>. The controls themselves live on
// the quest screen (QuestTools), where a child actually needs them.

import { createContext, useCallback, useContext, useEffect, useMemo, useState, type ReactNode } from 'react'

export interface Prefs {
  contrast: 'normal' | 'high'
  zoom: number          // 1 = 100%, up to 1.6 = 160%
  reducedMotion: boolean
}

export const ZOOM_MIN = 1
export const ZOOM_MAX = 1.6
export const ZOOM_STEP = 0.15

const DEFAULT: Prefs = { contrast: 'normal', zoom: 1, reducedMotion: false }
const KEY = 'dori.prefs'

const Ctx = createContext<{ prefs: Prefs; set: (p: Partial<Prefs>) => void }>({ prefs: DEFAULT, set: () => {} })

export function PrefsProvider({ children }: { children: ReactNode }) {
  const [prefs, setPrefs] = useState<Prefs>(() => {
    try {
      const raw = localStorage.getItem(KEY)
      const sys = window.matchMedia?.('(prefers-reduced-motion: reduce)').matches ?? false
      if (raw) {
        const saved = JSON.parse(raw) as Partial<Prefs>
        return { ...DEFAULT, reducedMotion: sys, ...saved, zoom: clampZoom(saved.zoom ?? 1) }
      }
      return { ...DEFAULT, reducedMotion: sys }
    } catch {
      return DEFAULT
    }
  })
  const set = useCallback((p: Partial<Prefs>) => setPrefs((prev) => ({ ...prev, ...p })), [])
  useEffect(() => {
    const el = document.documentElement
    el.dataset.contrast = prefs.contrast
    el.dataset.motion = prefs.reducedMotion ? 'reduced' : 'normal'
    el.style.setProperty('--step', `${prefs.zoom}rem`)
    try { localStorage.setItem(KEY, JSON.stringify(prefs)) } catch { /* ignore */ }
  }, [prefs])
  const value = useMemo(() => ({ prefs, set }), [prefs, set])
  return <Ctx.Provider value={value}>{children}</Ctx.Provider>
}

export const usePrefs = () => useContext(Ctx)

function clampZoom(z: number) {
  return Math.min(ZOOM_MAX, Math.max(ZOOM_MIN, Number.isFinite(z) ? z : 1))
}

/* Small inline icons so the toolbar reads as icons, not text. */
const ContrastIcon = () => (
  <svg width="22" height="22" viewBox="0 0 24 24" aria-hidden="true">
    <circle cx="12" cy="12" r="9" fill="none" stroke="currentColor" strokeWidth="2" />
    <path d="M12 3a9 9 0 0 1 0 18z" fill="currentColor" />
  </svg>
)
const ZoomIcon = () => (
  <svg width="22" height="22" viewBox="0 0 24 24" aria-hidden="true" fill="none" stroke="currentColor" strokeWidth="2.2" strokeLinecap="round">
    <circle cx="10.5" cy="10.5" r="6.5" />
    <path d="M15.5 15.5 21 21M8 10.5h5M10.5 8v5" />
  </svg>
)
const MotionIcon = () => (
  <svg width="22" height="22" viewBox="0 0 24 24" aria-hidden="true" fill="none" stroke="currentColor" strokeWidth="2.2" strokeLinecap="round">
    <path d="M3 12c3-5 6-5 9 0s6 5 9 0" />
    <path d="M5 5l14 14" />
  </svg>
)

/** Icon-only display controls shown on the quest screen. */
export function QuestTools() {
  const { prefs, set } = usePrefs()
  const high = prefs.contrast === 'high'
  const pct = Math.round(prefs.zoom * 100)
  return (
    <div className="tools" role="group" aria-label="Display settings">
      <button type="button" className="tool" aria-pressed={high} aria-label="High contrast" title="High contrast"
        onClick={() => set({ contrast: high ? 'normal' : 'high' })}>
        <ContrastIcon />
      </button>

      <div className="tool zoom" title="Zoom">
        <span className="zoom-ico"><ZoomIcon /></span>
        <input
          type="range" min={ZOOM_MIN} max={ZOOM_MAX} step={ZOOM_STEP} value={prefs.zoom}
          aria-label="Zoom level" aria-valuetext={`${pct} percent`}
          onChange={(e) => set({ zoom: clampZoom(parseFloat(e.target.value)) })}
        />
        <span className="zoom-pct" aria-hidden="true">{pct}%</span>
      </div>

      <button type="button" className="tool" aria-pressed={prefs.reducedMotion} aria-label="Less motion" title="Less motion"
        onClick={() => set({ reducedMotion: !prefs.reducedMotion })}>
        <MotionIcon />
      </button>
    </div>
  )
}
