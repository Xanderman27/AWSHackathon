import { useEffect, useState } from 'react'
import { api, getSession } from '../api'
import MessagesWidget from '../components/MessagesWidget'
import GroupActivityManager from '../components/GroupActivityManager'
import RoleGate from './RoleGate'

interface Row { student_id: string; display_name: string; has_goal_link: boolean; skill_name: string; band: string; estimate: number; confidence: string; evidence_count: number }
interface Summary { class_id: string; students: { id: string; display_name: string }[]; mastery: Row[]; counts: { needs_more_evidence: number; ready_for_extension: number } }
interface Evidence { student_id: string; evidence: { at: string; prompt: string; difficulty: number; correct: boolean; hint_used: boolean; route_reason?: string | null }[] }

const BAND_TONE: Record<string, string> = { 'Building foundations': 'cream', Practicing: 'sky', 'Ready for extension': 'mint' }
const CONF_TONE: Record<string, string> = { low: 'rose', medium: 'cream', high: 'mint' }

export default function TeacherDashboard() {
  const session = getSession()
  const [data, setData] = useState<Summary | null>(null)
  const [open, setOpen] = useState<Evidence | null>(null)
  const [err, setErr] = useState<string | null>(null)

  useEffect(() => { api<Summary>('/teacher/class').then(setData).catch((e) => setErr(String(e))) }, [])

  if (!session || session.role !== 'teacher') return <RoleGate need="teacher" />
  if (err) return <p role="alert">{err}</p>
  if (!data) return <p>Loading…</p>

  const without = data.students.filter((s) => !data.mastery.some((m) => m.student_id === s.id))
  const openName = open && data.students.find((s) => s.id === open.student_id)?.display_name

  return (
    <div className="page">
      <div className="row between">
        <div>
          <span className="chip sky">Class 4A</span>
          <h1 style={{ marginTop: 10 }}>Equivalent fractions</h1>
          <p className="muted" style={{ margin: 0 }}>CCSS 4.NF.A.1 · updated just now</p>
        </div>
        <button type="button" className="btn-primary">Assign a quest</button>
      </div>

      <div className="grid-3">
        <div className="card tinted-cream"><div className="stat">{data.counts.needs_more_evidence + without.length}</div><div className="stat-label">learners need more evidence</div></div>
        <div className="card tinted-mint"><div className="stat">{data.counts.ready_for_extension}</div><div className="stat-label">learners are ready for extension</div></div>
        <div className="card tinted-sky"><div className="stat">{data.students.length - without.length}<span style={{ fontSize: '0.5em', opacity: 0.7 }}>/{data.students.length}</span></div><div className="stat-label">have completed a quest</div></div>
      </div>

      <div className="card">
        <div className="row between" style={{ marginBottom: 8 }}><h2 style={{ margin: 0 }}>Learners</h2><span className="muted">Neutral language by design. No rankings.</span></div>
        <table>
          <thead><tr><th>Learner</th><th>Skill</th><th>Where they are</th><th>Estimate</th><th>Confidence</th><th>Evidence</th><th></th></tr></thead>
          <tbody>
            {data.mastery.map((m) => (
              <tr key={m.student_id + m.skill_name}>
                <td><span className="avatar" aria-hidden="true">{m.display_name[0]}</span>{m.display_name} {m.has_goal_link && <span className="chip" title="Has a linked goal (teacher-only)" style={{ marginLeft: 6 }}>goal</span>}</td>
                <td className="muted">{m.skill_name}</td>
                <td><span className={`chip ${BAND_TONE[m.band]}`}>{m.band}</span></td>
                <td><span className="bar" aria-hidden="true"><i style={{ width: `${Math.round(m.estimate * 100)}%` }} /></span> <span className="muted">{m.estimate.toFixed(2)}</span></td>
                <td><span className={`chip ${CONF_TONE[m.confidence]}`}>{m.confidence}</span></td>
                <td>{m.evidence_count} {m.evidence_count === 1 ? "item" : "items"}</td>
                <td><button type="button" className="table-btn" onClick={() => api<Evidence>(`/teacher/students/${m.student_id}`).then(setOpen)}>Evidence</button></td>
              </tr>
            ))}
            {without.map((s) => (
              <tr key={s.id}><td><span className="avatar" aria-hidden="true">{s.display_name[0]}</span>{s.display_name}</td><td colSpan={5} className="muted">No quest completed yet</td><td></td></tr>
            ))}
          </tbody>
        </table>
      </div>

      {open && (
        <div className="card" role="region" aria-label="Item evidence">
          <div className="row between"><h2 style={{ margin: 0 }}>Evidence for {openName}</h2><button type="button" onClick={() => setOpen(null)}>Close</button></div>
          {open.evidence.length === 0 ? <p className="muted" style={{ marginTop: 12 }}>No item responses yet. Ask the learner to try a quest.</p> : (
            <table style={{ marginTop: 12 }}>
              <thead><tr><th>Question</th><th>Difficulty</th><th>Result</th><th>Hint</th><th>Note</th></tr></thead>
              <tbody>
                {open.evidence.map((e, i) => (
                  <tr key={i}><td>{e.prompt}</td><td>{e.difficulty}</td><td><span className={`chip ${e.correct ? 'mint' : 'sky'}`}>{e.correct ? 'correct' : 'not yet'}</span></td><td>{e.hint_used ? '💡 used' : ''}</td><td className="muted">{e.route_reason ?? ''}</td></tr>
                ))}
              </tbody>
            </table>
          )}
        </div>
      )}

      <GroupActivityManager />
      <MessagesWidget />

      <div className="card" style={{ background: 'var(--surface-2)' }}>
        <strong>How this works.</strong> <span className="muted">After every answer we update one number per skill: how likely it is that this learner knows it. Items are calibrated so the model knows which questions are hard, and the next question is the one that tells us the most without being discouraging. Nothing here diagnoses, grades, or places a student.</span>
      </div>
    </div>
  )
}
