// The practice path: one winding track per skill, Duolingo-style. Steps show how far the
// learner has come; tapping a reachable step starts a practice quest on that skill. No
// scores or labels are ever shown here — just the path.

import { useEffect, useState } from 'react'
import { useNavigate } from 'react-router-dom'
import { api } from '../api'

interface Track {
  skill_id: string; unit: number; title: string; subject: string
  steps_done: number; total_steps: number; started: boolean
}

const TONE = ['g', 'b', 'p']
// Gentle S-curve for the five steps plus the trophy.
const OFFSETS = [0, -62, -88, -62, 0, 58]

export default function StudentPath() {
  const nav = useNavigate()
  const [tracks, setTracks] = useState<Track[]>([])
  const [stars, setStars] = useState(0)
  const [err, setErr] = useState<string | null>(null)

  useEffect(() => {
    api<{ tracks: Track[]; stars: number }>('/student/path')
      .then((d) => { setTracks(d.tracks); setStars(d.stars) })
      .catch((e) => setErr(String(e)))
  }, [])

  if (err) return <p role="alert">Something went wrong. {err}</p>

  return (
    <div className="stack">
      <div className="row between">
        <h2 className="section-title" style={{ margin: 0 }}>My path</h2>
        <span className="stars-chip" aria-label={`${stars} stars earned`}>⭐ {stars}</span>
      </div>
      <p className="muted helper" style={{ marginTop: -8 }}>
        Follow your path! Tap a green circle to practice. Gold circles are ones you've earned.
      </p>

      <div className="path-wrap">
        {tracks.map((t, ti) => {
          const complete = t.steps_done >= t.total_steps
          return (
            <section key={t.skill_id} className="unit">
              <header className={`unit-banner ${TONE[ti % TONE.length]}`}>
                <div>
                  <div className="k">Unit {t.unit} · {t.subject === 'math' ? 'Math' : 'Reading'}</div>
                  <h2>{cap(t.title)}</h2>
                </div>
                <span className="unit-count" aria-hidden="true">{t.steps_done}/{t.total_steps}</span>
              </header>

              <div className="path" role="list" aria-label={`Steps for ${t.title}`}>
                {Array.from({ length: t.total_steps }, (_, i) => {
                  const state = i < t.steps_done ? 'done' : i === t.steps_done ? 'current' : 'locked'
                  const label = state === 'done'
                    ? `Step ${i + 1} of ${t.total_steps}, earned. Practice again.`
                    : state === 'current'
                      ? `Step ${i + 1} of ${t.total_steps}, up next. Start practicing.`
                      : `Step ${i + 1} of ${t.total_steps}, not yet.`
                  return (
                    <div key={i} role="listitem"
                      className={`node-slot ${state === 'current' ? 'bob' : ''}`}
                      style={{ ['--dx' as string]: `${OFFSETS[i]}px` }}>
                      {state === 'current' && <span className="start-tip" aria-hidden="true">START</span>}
                      <button type="button" className={`node ${state}`} disabled={state === 'locked'}
                        aria-label={label}
                        onClick={() => nav(`/student/quest/${t.skill_id}`)}>
                        <span aria-hidden="true">{state === 'done' ? '✓' : '★'}</span>
                      </button>
                    </div>
                  )
                })}
                <div className="node-slot" style={{ ['--dx' as string]: `${OFFSETS[t.total_steps]}px` }}>
                  <div className={`node trophy ${complete ? 'won' : ''}`} aria-hidden="true">🏆</div>
                </div>
              </div>
            </section>
          )
        })}
      </div>
    </div>
  )
}

const cap = (s: string) => s.charAt(0).toUpperCase() + s.slice(1)
