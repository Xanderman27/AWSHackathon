// A light confetti burst for a correct answer. No dependency, no sound, and it never fires
// when the learner has asked for less motion.

import { useEffect, useState } from 'react'
import { usePrefs } from '../a11y'

const COLORS = ['#2869dd', '#f4c45b', '#57b894', '#ef8fa8', '#8ec5e8']

interface Piece { id: number; dx: number; dy: number; rot: number; color: string; delay: number }

export default function Confetti({ burst }: { burst: number }) {
  const { prefs } = usePrefs()
  const [pieces, setPieces] = useState<Piece[]>([])

  useEffect(() => {
    if (!burst || prefs.reducedMotion) return
    const made: Piece[] = Array.from({ length: 20 }, (_, i) => {
      const angle = (-140 + Math.random() * 100) * (Math.PI / 180)
      const dist = 120 + Math.random() * 130
      return {
        id: burst * 100 + i,
        dx: Math.cos(angle) * dist * (Math.random() < 0.5 ? -1 : 1),
        dy: Math.sin(angle) * dist,
        rot: Math.random() * 540 - 270,
        color: COLORS[i % COLORS.length],
        delay: Math.random() * 0.12,
      }
    })
    setPieces(made)
    const t = setTimeout(() => setPieces([]), 1700)
    return () => clearTimeout(t)
  }, [burst, prefs.reducedMotion])

  if (!pieces.length) return null

  return (
    <div className="confetti-layer" aria-hidden="true">
      {pieces.map((p) => (
        <span key={p.id} className="confetti-piece" style={{
          background: p.color,
          animationDelay: `${p.delay}s`,
          ['--dx' as string]: `${p.dx}px`,
          ['--dy' as string]: `${p.dy}px`,
          ['--rot' as string]: `${p.rot}deg`,
        }} />
      ))}
    </div>
  )
}
