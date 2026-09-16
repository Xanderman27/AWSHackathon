import { useEffect, useState } from 'react'
import { api } from '../api'
import ConferenceScheduler from './ConferenceScheduler'

interface Child { id: string; display_name: string; grade: number }
interface NextStep {
  id: string; title: string; why: string; minutes: number
  materials: string[]; steps: string[]; approved_by: string; approved_on: string
}
interface Progress {
  student: Child
  what_we_practiced: { skill: string; practiced: string; sessions: number }[]
  next_steps: NextStep[]
}

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

  const { student, what_we_practiced: practiced, next_steps: next } = progress

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
        <p className="muted" style={{ margin: 0 }}>What your child practiced and what comes next, in plain language.</p>
      </div>

      <div className="grid-2">
        <div className="card tinted-mint">
          <h2>What we practiced</h2>
          {practiced.length === 0
            ? <p>{student.display_name} has not started a quest yet.</p>
            : practiced.map((p, i) => (
              <p key={i} style={{ fontSize: '1.1em' }}>
                {p.practiced} <span style={{ opacity: 0.75 }}>({p.sessions} check-ins so far)</span>
              </p>
            ))}
        </div>
        <div className="card tinted-sky">
          <h2>Where this fits</h2>
          <p>These are short practice check-ins, not tests. Nothing here changes your child's IEP or 504 plan.</p>
          <p style={{ marginBottom: 0 }}>Your child's teacher reviews every suggestion before you see it.</p>
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
                <p className="muted" style={{ margin: 0, fontSize: '0.85em' }}>
                  Approved by {n.approved_by} on {n.approved_on}
                </p>
              </div>
            ))}
          </div>
        )}
      </div>

      <ConferenceScheduler studentId={student.id} />
    </div>
  )
}
