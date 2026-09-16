// A family-facing mastery gauge for one child. Score is 0-4. Zones follow the learner-model
// bands: building (<1.6), practicing (1.6-3.2), ready (3.2-3.7), stretching (3.7-4).

const ZONES = [
  { from: 0, to: 1.6, color: 'var(--zone-red)' },
  { from: 1.6, to: 3.2, color: 'var(--zone-yellow)' },
  { from: 3.2, to: 3.7, color: 'var(--zone-green)' },
  { from: 3.7, to: 4, color: 'var(--zone-blue)' },
]

const CX = 100, CY = 100, R = 82, W = 22

function polar(score: number) {
  const a = Math.PI - (score / 4) * Math.PI  // 0 -> left, 4 -> right
  return { x: CX + R * Math.cos(a), y: CY - R * Math.sin(a) }
}

function arc(from: number, to: number) {
  const s = polar(from), e = polar(to)
  const large = to - from > 2 ? 1 : 0
  return `M ${s.x} ${s.y} A ${R} ${R} 0 ${large} 1 ${e.x} ${e.y}`
}

export function MasteryGauge({ score, label = 'Average mastery score' }: { score: number | null; label?: string }) {
  const val = score ?? 0
  const dot = polar(Math.min(4, Math.max(0, val)))
  return (
    <figure className="gauge" aria-label={score == null ? 'No mastery score yet' : `${label}: ${val} out of 4`}>
      <svg viewBox="0 0 200 118" width="100%" role="img" aria-hidden="true">
        {ZONES.map((z) => (
          <path key={z.from} d={arc(z.from + 0.02, z.to - 0.02)} stroke={z.color} strokeWidth={W}
            fill="none" strokeLinecap="butt" />
        ))}
        {score != null && (
          <circle cx={dot.x} cy={dot.y} r="7" fill="var(--surface)" stroke="var(--ink)" strokeWidth="3" />
        )}
      </svg>
      <figcaption className="gauge-caption">
        <div className="gauge-num">{score == null ? '–' : val.toFixed(1)}</div>
        <div className="gauge-label">{label}</div>
      </figcaption>
    </figure>
  )
}

/** One skill on a 0-4 track with the child's position marked. */
export function OutcomeTrack({ score, band, evidence }: { score: number; band: string; evidence: number }) {
  const pct = Math.min(100, Math.max(0, (score / 4) * 100))
  return (
    <div className="track" role="img" aria-label={`${score} out of 4, ${band}, based on ${evidence} check-ins`}>
      <div className="track-bar">
        {ZONES.map((z) => (
          <i key={z.from} style={{ width: `${((z.to - z.from) / 4) * 100}%`, background: z.color }} />
        ))}
        <span className="track-dot" style={{ left: `${pct}%` }} />
      </div>
      <div className="track-scale" aria-hidden="true"><span>0</span><span>1</span><span>2</span><span>3</span><span>4</span></div>
    </div>
  )
}
