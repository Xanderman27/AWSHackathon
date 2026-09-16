// Accessibility preferences (PRD FR-06) and a read-aloud hook.
// Read-aloud uses the browser's speech engine as a stand-in; the Polly adapter swaps in behind the same hook.

import { createContext, useCallback, useContext, useEffect, useMemo, useState, type ReactNode } from 'react'

export interface Prefs {
  readAloud: boolean
  contrast: 'normal' | 'high'
  scale: 1 | 2 | 3
  reducedMotion: boolean
}

const DEFAULT: Prefs = { readAloud: false, contrast: 'normal', scale: 1, reducedMotion: false }
const KEY = 'alp.prefs'

const Ctx = createContext<{ prefs: Prefs; set: (p: Partial<Prefs>) => void }>({ prefs: DEFAULT, set: () => {} })

export function PrefsProvider({ children }: { children: ReactNode }) {
  const [prefs, setPrefs] = useState<Prefs>(() => {
    try {
      const raw = localStorage.getItem(KEY)
      const sys = window.matchMedia?.('(prefers-reduced-motion: reduce)').matches ?? false
      return raw ? { ...DEFAULT, ...JSON.parse(raw) } : { ...DEFAULT, reducedMotion: sys }
    } catch {
      return DEFAULT
    }
  })
  const set = useCallback((p: Partial<Prefs>) => setPrefs((prev) => ({ ...prev, ...p })), [])
  useEffect(() => {
    const el = document.documentElement
    el.dataset.contrast = prefs.contrast
    el.dataset.scale = String(prefs.scale)
    el.dataset.motion = prefs.reducedMotion ? 'reduced' : 'normal'
    try { localStorage.setItem(KEY, JSON.stringify(prefs)) } catch { /* ignore */ }
  }, [prefs])
  const value = useMemo(() => ({ prefs, set }), [prefs, set])
  return <Ctx.Provider value={value}>{children}</Ctx.Provider>
}

export const usePrefs = () => useContext(Ctx)

export function useSpeech() {
  const synth = typeof window !== 'undefined' ? window.speechSynthesis : undefined
  const speak = useCallback((text: string) => {
    if (!synth) return
    synth.cancel()
    const u = new SpeechSynthesisUtterance(text)
    u.rate = 0.9
    synth.speak(u)
  }, [synth])
  const pause = useCallback(() => synth?.pause(), [synth])
  const resume = useCallback(() => synth?.resume(), [synth])
  const stop = useCallback(() => synth?.cancel(), [synth])
  return { speak, pause, resume, stop, available: !!synth }
}

export function AccessibilityBar() {
  const { prefs, set } = usePrefs()
  return (
    <div className="a11y-bar" role="group" aria-label="Accessibility settings">
      <button type="button" aria-pressed={prefs.readAloud} onClick={() => set({ readAloud: !prefs.readAloud })}>
        🔊 Read aloud {prefs.readAloud ? 'on' : 'off'}
      </button>
      <button type="button" aria-pressed={prefs.contrast === 'high'} onClick={() => set({ contrast: prefs.contrast === 'high' ? 'normal' : 'high' })}>
        ◐ High contrast {prefs.contrast === 'high' ? 'on' : 'off'}
      </button>
      <div className="seg" role="group" aria-label="Text size">
        {[1, 2, 3].map((s) => (
          <button key={s} type="button" aria-pressed={prefs.scale === s} onClick={() => set({ scale: s as 1 | 2 | 3 })} aria-label={`Text size ${s === 1 ? 'normal' : s === 2 ? 'large' : 'largest'}`}>
            {s === 1 ? 'A' : s === 2 ? 'A+' : 'A++'}
          </button>
        ))}
      </div>
      <button type="button" aria-pressed={prefs.reducedMotion} onClick={() => set({ reducedMotion: !prefs.reducedMotion })}>
        ✋ Less motion {prefs.reducedMotion ? 'on' : 'off'}
      </button>
    </div>
  )
}
