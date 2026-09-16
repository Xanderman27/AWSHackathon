import { useEffect, useState } from 'react'
import { api, getSession } from '../api'

interface Child { id: string; display_name: string; grade: number }
interface Progress { student: Child; what_we_practiced: { skill: string; practiced: string; sessions: number }[]; next_steps: unknown[]; conference: unknown }

export default function ParentView() {
  const session = getSession()
  const [children, setChildren] = useState<Child[]>([])
  const [progress, setProgress] = useState<Progress | null>(null)
  const [err, setErr] = useState<string | null>(null)

  useEffect(() => {
    api<Child[]>('/parent/children').then((c) => { setChildren(c); if (c[0]) api<Progress>(`/parent/children/${c[0].id}/progress`).then(setProgress) }).catch((e) => setErr(String(e)))
  }, [])

  if (!session || session.role !== 'parent') return <p>Please pick "I am a parent" on the home page.</p>
  if (err) return <p role="alert">{err}</p>

  return (
    <div className="stack">
      <div>
        <span className="chip cream">Family view</span>
        <h1 style={{ marginTop: 10 }}>{progress ? `${progress.student.display_name}'s progress` : 'Your child'}</h1>
        <p className="muted" style={{ margin: 0 }}>Grade {progress?.student.grade ?? ''} · what your child practiced and what comes next, in plain language.</p>
      </div>
      {children.length > 1 && (
        <div className="row" role="group" aria-label="Choose a child">
          {children.map((c) => <button key={c.id} type="button" aria-pressed={progress?.student.id === c.id} onClick={() => api<Progress>(`/parent/children/${c.id}/progress`).then(setProgress)}>{c.display_name}</button>)}
        </div>
      )}
      {progress && (
        <div className="grid-2">
          <div className="card tinted-mint">
            <h2>What we practiced</h2>
            {progress.what_we_practiced.length === 0 ? <p>{progress.student.display_name} has not started a quest yet.</p> : (
              progress.what_we_practiced.map((p, i) => <p key={i} style={{ fontSize: '1.1em' }}>{p.practiced}</p>)
            )}
          </div>
          <div className="card tinted-sky"><h2>What comes next</h2><p>Your child's teacher will add approved next steps here.</p></div>
          <div className="card" style={{ gridColumn: '1 / -1' }}>
            <div className="row between">
              <div><h2 style={{ marginBottom: 4 }}>Talk with the teacher</h2><p className="muted" style={{ margin: 0 }}>Pick a time that works for you. The teacher confirms it.</p></div>
              <button type="button" className="btn-primary" disabled>Request a time</button>
            </div>
          </div>
        </div>
      )}
      <p className="muted" style={{ fontSize: '0.9em' }}>This tool supports learning. It does not make eligibility, placement, or IEP decisions.</p>
    </div>
  )
}
