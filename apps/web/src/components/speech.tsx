// Read-aloud with word-level highlighting.
//
// One utterance covers the question and every choice. Each spoken word keeps its character
// offset in that utterance, so the browser's boundary events tell us exactly which word to
// highlight. Amazon Polly with speech marks replaces this later behind the same interface.

import { useCallback, useEffect, useRef, useState } from 'react'

export interface Token { text: string; start: number; end: number; region: string }

export function buildScript(parts: { region: string; text: string }[]) {
  let full = ''
  const tokens: Token[] = []
  parts.forEach((part, pi) => {
    if (pi > 0) full += '. '
    const words = part.text.split(/\s+/).filter(Boolean)
    words.forEach((w, i) => {
      const start = full.length
      full += w
      tokens.push({ text: w, start, end: full.length, region: part.region })
      if (i < words.length - 1) full += ' '
    })
  })
  return { full, tokens }
}

export type PlayState = 'idle' | 'playing' | 'paused'

export function useNarrator() {
  const [state, setState] = useState<PlayState>('idle')
  const [charIndex, setCharIndex] = useState(-1)
  const synth = typeof window !== 'undefined' ? window.speechSynthesis : undefined
  const held = useRef<SpeechSynthesisUtterance | null>(null)

  const stop = useCallback(() => {
    try { synth?.cancel() } catch { /* unsupported */ }
    held.current = null
    setState('idle'); setCharIndex(-1)
  }, [synth])

  const play = useCallback((text: string) => {
    if (!synth) return
    try {
      synth.cancel()
      const u = new SpeechSynthesisUtterance(text)
      u.rate = 0.85
      u.onboundary = (e) => { if (typeof e.charIndex === 'number') setCharIndex(e.charIndex) }
      u.onend = () => { setState('idle'); setCharIndex(-1) }
      u.onerror = () => { setState('idle'); setCharIndex(-1) }
      held.current = u
      synth.speak(u)
      setState('playing')
    } catch { setState('idle') }
  }, [synth])

  /** One button: play, then pause, then resume. */
  const toggle = useCallback((text: string) => {
    if (!synth) return
    if (state === 'playing') { try { synth.pause() } catch { /* ignore */ } setState('paused'); return }
    if (state === 'paused' && held.current) { try { synth.resume() } catch { /* ignore */ } setState('playing'); return }
    play(text)
  }, [state, synth, play])

  useEffect(() => () => { try { synth?.cancel() } catch { /* ignore */ } }, [synth])

  return { state, charIndex, toggle, play, stop, available: !!synth }
}

/** Renders one region of the script with the spoken word highlighted. */
export function SpokenText({ tokens, region, charIndex, playing, className = '' }: {
  tokens: Token[]; region: string; charIndex: number; playing: boolean; className?: string
}) {
  const mine = tokens.filter((t) => t.region === region)
  // If the browser never reports boundaries, fall back to marking the whole block as reading.
  const tracking = charIndex >= 0
  return (
    <span className={`${className} ${playing && !tracking ? 'reading-block' : ''}`}>
      {mine.map((t, i) => {
        const now = tracking && charIndex >= t.start && charIndex < t.end
        return <span key={i} className={now ? 'word now' : 'word'}>{t.text}{i < mine.length - 1 ? ' ' : ''}</span>
      })}
    </span>
  )
}
