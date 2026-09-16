import { useEffect, useState } from 'react'
import { api } from '../api'
import { MasteryGauge, OutcomeTrack } from '../components/MasteryGauge'
import ConferenceScheduler from './ConferenceScheduler'

interface Child { id: string; display_name: string; grade: number }
interface NextStep {
  id: string; title: string; why: string; minutes: number
  materials: string[]; steps: string[]; approved_by: string; approved_on: string
}
interface MasteryRow {
  skill_id: string; skill: string; child_name: string; estimate: number; score: number
  band: string; band_label: string; evidence_count: number; history: number[]
}
interface Progress {
  student: Child
  what_we_practiced: { skill: string; practiced: string; sessions: number }[]
  next_steps: NextStep[]
  mastery: MasteryRow[]
  average_score: number | null
}

const BAND_TONE: Record<string, string> = { building: 'cream', practicing: 'sky', extension: 'mint' }

export default function ParentProgress() {
  const [children, setChildren] = useState<Child[]>([])
  const [progress, setProgress] = useState<Progress | null>(null)
  const [err, setErr] = useState<string | null>(null)

  useEffect(() => {
    api<Child[]>('/parent/children')
      .then((c) => { setChildren(c); if (c[0]) return api<Progress>(`/parent/children/${c[0].id}/progress`).then(setProgress) })
      .catch((e) => setErr(String(e)))
  }, [])

  if (err) return <p role="alert">{err}</p>
  if (!progress) return <p>Loading…</p>

  const { student, next_steps: next, mastery, average_score: avg } = progress

  return (
    <div className="stack">
      {children.length > 1 && (
        <div className="row" role="group" aria-label="Choose a child">
          {children.map((c) => (
            <button key={c.id} type="button" aria-pressed={student.id === c.id}
              onClick={() => api<Progress>(`/parent/children/${c.id}/progress`).then(setProgress)}>
              {c.display_name}
            </button>
          ))}
        </div>
      )}

      <div>
        <h2 style={{ marginBottom: 2 }}>{student.display_name}, Grade {student.grade}</h2>
        <p className="muted" style={{ margin: 0 }}>Only {student.display_name}'s own progress. No class ranks, no comparisons.</p>
      </div>

      <div className="card">
        <div className="mastery-grid">
          <div>
            <h3 style={{ marginBottom: 4 }}>Mastery <span className="muted" style={{ fontWeight: 500, fontSize: '.85em' }}>(0 to 4)</span></h3>
            <MasteryGauge score={avg} label="Average mastery score" />
            <div className="legend" aria-hidden="true">
              <span><i style={{ background: 'var(--zone-red)' }} />Building</span>
              <span><i style={{ background: 'var(--zone-yellow)' }} />Practicing</span>
              <span><i style={{ background: 'var(--zone-green)' }} />Ready</span>
              <span><i style={{ background: 'var(--zone-blue)' }} />Stretching</span>
            </div>
          </div>
          <div>
            <h3 style={{ marginBottom: 4 }}>Outcomes</h3>
            {mastery.length === 0 ? (
              <p className="muted">{student.display_name} has not started a quest yet, so there is nothing to show.</p>
            ) : mastery.map((m) => (
              <div className="outcome" key={m.skill_id}>
                <div className="outcome-head">
                  <strong>{student.display_name} can work on {m.child_name}</strong>
                  <span className="row" style={{ gap: 8 }}>
                    <span className={`chip ${BAND_TONE[m.band]}`}>{m.band_label}</span>
                    <span className="chip">{m.score.toFixed(1)} / 4</span>
                  </span>
                </div>
                <OutcomeTrack score={m.score} band={m.band_label} evidence={m.evidence_count} />
                <span className="muted" style={{ fontSize: '.85em' }}>Based on {m.evidence_count} check-in{m.evidence_count === 1 ? '' : 's'}</span>
              </div>
            ))}
          </div>
        </div>
      </div>

      <div>
        <div className="row between" style={{ marginBottom: 12 }}>
          <h2 style={{ margin: 0 }}>What comes next</h2>
          <span className="chip mint">Approved by the teacher</span>
        </div>
        {next.length === 0 ? (
          <div className="card"><p className="muted" style={{ margin: 0 }}>Your child's teacher has not added next steps yet.</p></div>
        ) : (
          <div className="grid-2">
            {next.map((n) => (
              <div className="card next-step" key={n.id}>
                <h3 style={{ margin: 0 }}>{n.title}</h3>
                <p className="muted" style={{ margin: 0 }}>{n.why}</p>
                <div className="meta">
                  <span className="chip cream">⏱ {n.minutes} minutes</span>
                  {n.materials.length > 0 && <span className="chip">🧰 {n.materials.join(', ')}</span>}
                </div>
                <ol>{n.steps.map((s, i) => <li key={i}>{s}</li>)}</ol>
                <p className="muted" style={{ margin: 0, fontSize: '0.85em' }}>Approved by {n.approved_by} on {n.approved_on}</p>
              </div>
            ))}
          </div>
        )}
      </div>

      <ConferenceScheduler studentId={student.id} />
    </div>
  )
}
