// The practice path: subjects down the left, a winding Duolingo-style track on the right,
// with little illustrations beside the steps (a pirate flag on the history track, a rocket
// on science, and so on). No scores or labels are ever shown here — just the path.

import { useEffect, useMemo, useState, type ComponentType } from 'react'
import { useNavigate } from 'react-router-dom'
import { api } from '../api'
import Capy from '../components/Capy'
import {
  AbacusIcon, BookIcon, CastleIcon, FlaskIcon, GlobeIcon, PencilIcon,
  PirateFlagIcon, RocketIcon, ShapesIcon, TreasureMapIcon,
} from '../components/PathArt'

interface Track {
  skill_id: string; unit: number; title: string; subject: string
  steps_done: number; total_steps: number; started: boolean
}

type Icon = ComponentType<{ size?: number; className?: string }>

const SUBJECTS: { id: string; label: string; RailIcon: Icon; decor: [Icon, Icon]; tone: string }[] = [
  { id: 'english', label: 'English', RailIcon: BookIcon, decor: [PencilIcon, BookIcon], tone: 'p' },
  { id: 'science', label: 'Science', RailIcon: FlaskIcon, decor: [RocketIcon, FlaskIcon], tone: 'g' },
  { id: 'math', label: 'Math', RailIcon: ShapesIcon, decor: [AbacusIcon, ShapesIcon], tone: 'b' },
  { id: 'history', label: 'History', RailIcon: CastleIcon, decor: [PirateFlagIcon, CastleIcon], tone: 'g' },
  { id: 'geography', label: 'Geography', RailIcon: GlobeIcon, decor: [TreasureMapIcon, GlobeIcon], tone: 'b' },
]

// Gentle S-curve for the five steps plus the trophy.
const OFFSETS = [0, -62, -88, -62, 0, 58]

export default function StudentPath() {
  const nav = useNavigate()
  const [tracks, setTracks] = useState<Track[]>([])
  const [subject, setSubject] = useState<string>('english')
  const [err, setErr] = useState<string | null>(null)
  // A subject's path stays hidden until the learner does a short check-in for it. The
  // check-in only tunes which questions appear afterwards — the path itself always
  // starts at zero, because steps are growth, not a head start.
  const [benchmarks, setBenchmarks] = useState<Record<string, string | null>>({})
  const [benchSkill, setBenchSkill] = useState<Record<string, string>>({})
  const [loaded, setLoaded] = useState(false)

  useEffect(() => {
    api<{ tracks: Track[]; stars: number; benchmarks: Record<string, string | null>; bench_skill: Record<string, string> }>('/student/path')
      .then((d) => { setTracks(d.tracks); setBenchmarks(d.benchmarks); setBenchSkill(d.bench_skill); setLoaded(true) })
      .catch((e) => setErr(String(e)))
  }, [])

  const bySubject = useMemo(() => {
    const m = new Map<string, Track[]>()
    for (const t of tracks) {
      if (!m.has(t.subject)) m.set(t.subject, [])
      m.get(t.subject)!.push(t)
    }
    return m
  }, [tracks])

  if (err) return <p role="alert">Something went wrong. {err}</p>

  const meta = SUBJECTS.find((s) => s.id === subject) ?? SUBJECTS[0]
  const mine = bySubject.get(subject) ?? []
  const [DecorA, DecorB] = meta.decor
  const gated = loaded && mine.length > 0 && !benchmarks[subject]

  return (
    <div className="stack">
      <h2 className="section-title" style={{ margin: 0 }}>My path</h2>

      <div className="path-layout">
        <nav className="subject-rail" aria-label="Subjects">
          {SUBJECTS.map((s) => {
            const ts = bySubject.get(s.id) ?? []
            const done = ts.reduce((a, t) => a + t.steps_done, 0)
            const total = ts.reduce((a, t) => a + t.total_steps, 0)
            const Icon = s.RailIcon
            return (
              <button key={s.id} type="button" className="subj" aria-pressed={subject === s.id}
                onClick={() => setSubject(s.id)}>
                <span className="subj-ico"><Icon size={34} /></span>
                <span className="subj-text">
                  {s.label}
                  <small>{total === 0 ? 'Coming soon'
                    : !benchmarks[s.id] && loaded ? 'Take your check-in!'
                    : `${done} of ${total} steps`}</small>
                </span>
              </button>
            )
          })}
        </nav>

        <div className="path-wrap">
          {mine.length === 0 && (
            <div className="card celebrate" style={{ padding: 32 }}>
              <div style={{ width: 96, margin: '0 auto 8px' }}><meta.RailIcon size={96} /></div>
              <h2>Coming soon!</h2>
              <p className="muted" style={{ margin: 0 }}>New {meta.label} adventures are on the way.</p>
            </div>
          )}
          {gated && (
            <div className={`card celebrate bench-cta tinted-${meta.tone === 'p' ? 'cream' : meta.tone === 'b' ? 'sky' : 'mint'} pop`}>
              <Capy size={132} mood="cheer" float />
              <h2 style={{ marginTop: 10 }}>Ready for {meta.label}?</h2>
              <p className="bench-copy">
                Do a quick check-in with Capy first! It's short, there are no grades, and it
                helps us pick the just-right questions for you.
              </p>
              <button type="button" className="btn-primary btn-lg bench-go"
                onClick={() => nav(`/student/quest/${benchSkill[subject]}?bench=${subject}`)}>
                Start my check-in ✨
              </button>
              <p className="muted" style={{ margin: '10px 0 0', fontSize: '.9em' }}>
                Your path appears as soon as you finish!
              </p>
            </div>
          )}
          {!gated && mine.map((t) => {
            const complete = t.steps_done >= t.total_steps
            return (
              <section key={t.skill_id} className="unit">
                <header className={`unit-banner ${meta.tone}`}>
                  <div>
                    <div className="k">{meta.label} · Unit {t.unit}</div>
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
                        {i === 1 && <span className="deco deco-r"><DecorA size={62} /></span>}
                        {i === 3 && <span className="deco deco-l"><DecorB size={62} /></span>}
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
    </div>
  )
}

const cap = (s: string) => s.charAt(0).toUpperCase() + s.slice(1)
