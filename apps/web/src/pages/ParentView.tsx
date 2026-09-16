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
      <h1>Your child's progress</h1>
      {children.length > 1 && (
        <div className="row" role="group" aria-label="Choose a child">
          {children.map((c) => <button key={c.id} type="button" aria-pressed={progress?.student.id === c.id} onClick={() => api<Progress>(`/parent/children/${c.id}/progress`).then(setProgress)}>{c.display_name}</button>)}
        </div>
      )}
      {progress && (
        <>
          <div className="card">
            <h2>What we practiced</h2>
            {progress.what_we_practiced.length === 0 ? <p className="muted">{progress.student.display_name} has not started a quest yet.</p> : (
              <ul>{progress.what_we_practiced.map((p, i) => <li key={i}>{p.practiced}</li>)}</ul>
            )}
          </div>
          <div className="card"><h2>What comes next</h2><p className="muted">Your child's teacher will add approved next steps here.</p></div>
          <div className="card"><h2>Talk with the teacher</h2><p className="muted">Conference requests are coming in the next build.</p><button type="button" disabled>Request a time</button></div>
        </>
      )}
      <p className="muted">This tool supports learning. It does not make eligibility, placement, or IEP decisions.</p>
    </div>
  )
}
