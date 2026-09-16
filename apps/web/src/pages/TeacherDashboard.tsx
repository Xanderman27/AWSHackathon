import { useEffect, useState } from 'react'
import { api, getSession } from '../api'

interface Row { student_id: string; display_name: string; has_goal_link: boolean; skill_name: string; band: string; estimate: number; confidence: string; evidence_count: number }
interface Summary { class_id: string; students: { id: string; display_name: string }[]; mastery: Row[]; counts: { needs_more_evidence: number; ready_for_extension: number } }
interface Evidence { student_id: string; evidence: { at: string; prompt: string; difficulty: number; correct: boolean; hint_used: boolean; route_reason?: string | null }[] }

export default function TeacherDashboard() {
  const session = getSession()
  const [data, setData] = useState<Summary | null>(null)
  const [open, setOpen] = useState<Evidence | null>(null)
  const [err, setErr] = useState<string | null>(null)

  useEffect(() => { api<Summary>('/teacher/class').then(setData).catch((e) => setErr(String(e))) }, [])

  if (!session || session.role !== 'teacher') return <p>Please pick "I am a teacher" on the home page.</p>
  if (err) return <p role="alert">{err}</p>
  if (!data) return <p>Loading…</p>

  const without = data.students.filter((s) => !data.mastery.some((m) => m.student_id === s.id))

  return (
    <div className="stack">
      <h1>Class {data.class_id.replace('class-', '').toUpperCase()} · Equivalent fractions</h1>
      <div className="row">
        <div className="card"><div className="stat">{data.counts.needs_more_evidence + without.length}</div>learners need more evidence</div>
        <div className="card"><div className="stat">{data.counts.ready_for_extension}</div>learners are ready for extension</div>
        <div className="card"><div className="stat">{data.students.length - without.length}/{data.students.length}</div>have completed a quest</div>
      </div>

      <div className="card">
        <h2>Learners</h2>
        <table>
          <thead><tr><th>Name</th><th>Skill</th><th>Where they are</th><th>Confidence</th><th>Evidence</th><th></th></tr></thead>
          <tbody>
            {data.mastery.map((m) => (
              <tr key={m.student_id + m.skill_name}>
                <td>{m.display_name} {m.has_goal_link && <span className="pill" title="Has a linked goal (teacher-only)">goal</span>}</td>
                <td>{m.skill_name}</td>
                <td><span className="pill">{m.band}</span> <span className="muted">{m.estimate.toFixed(2)}</span></td>
                <td>{m.confidence}</td>
                <td>{m.evidence_count} items</td>
                <td><button type="button" onClick={() => api<Evidence>(`/teacher/students/${m.student_id}`).then(setOpen)}>Evidence</button></td>
              </tr>
            ))}
            {without.map((s) => (
              <tr key={s.id}><td>{s.display_name}</td><td colSpan={4} className="muted">No quest completed yet</td><td></td></tr>
            ))}
          </tbody>
        </table>
      </div>

      {open && (
        <div className="card" role="region" aria-label="Item evidence">
          <div className="row" style={{ justifyContent: 'space-between' }}>
            <h2>Evidence for {data.students.find((s) => s.id === open.student_id)?.display_name}</h2>
            <button type="button" onClick={() => setOpen(null)}>Close</button>
          </div>
          {open.evidence.length === 0 ? <p className="muted">No item responses yet. Ask the student to try a quest.</p> : (
            <table>
              <thead><tr><th>Question</th><th>Difficulty</th><th>Result</th><th>Hint</th><th>Note</th></tr></thead>
              <tbody>
                {open.evidence.map((e, i) => (
                  <tr key={i}><td>{e.prompt}</td><td>{e.difficulty}</td><td>{e.correct ? 'correct' : 'not yet'}</td><td>{e.hint_used ? 'used' : ''}</td><td className="muted">{e.route_reason ?? ''}</td></tr>
                ))}
              </tbody>
            </table>
          )}
        </div>
      )}

      <div className="card muted">
        <strong>How this works.</strong> After every answer we update one number per skill: how likely it is that this learner knows it. Items are calibrated so the model knows which questions are hard, and the next question is the one that tells us the most without being discouraging. Nothing here diagnoses, grades, or places a student.
      </div>
    </div>
  )
}
