// Learners tab: who needs what, with the evidence one click away.

import { useEffect, useState } from 'react'
import { Link } from 'react-router-dom'
import { api } from '../api'
import Avatar, { type AvatarSpec } from '../components/Avatar'

interface Row {
  student_id: string; display_name: string; has_goal_link: boolean; skill_name: string
  band: string; estimate: number; confidence: string; evidence_count: number; quests_done: number
}
interface Learner { id: string; display_name: string; photo?: string | null; avatar?: AvatarSpec | null }
interface Summary {
  class_id: string; students: Learner[]; mastery: Row[]
  counts: { needs_more_evidence: number; ready_for_extension: number }
}
interface Evidence { student_id: string; evidence: { at: string; prompt: string; difficulty: number; correct: boolean; hint_used: boolean; route_reason?: string | null }[] }

const BAND_TONE: Record<string, string> = { 'Building foundations': 'cream', Practicing: 'sky', 'Ready for extension': 'mint' }
const CONF_TONE: Record<string, string> = { low: 'rose', medium: 'cream', high: 'mint' }

export default function TeacherDashboard() {
  const [data, setData] = useState<Summary | null>(null)
  const [open, setOpen] = useState<Evidence | null>(null)
  const [err, setErr] = useState<string | null>(null)

  useEffect(() => { api<Summary>('/teacher/class').then(setData).catch((e) => setErr(String(e))) }, [])

  if (err) return <p role="alert">{err}</p>
  if (!data) return <p>Loading…</p>

  const without = data.students.filter((s) => !data.mastery.some((m) => m.student_id === s.id))
  const face = (id: string) => data.students.find((s) => s.id === id)
  const openName = open && data.students.find((s) => s.id === open.student_id)?.display_name

  return (
    <div className="stack">
      <div className="row between">
        <p className="muted" style={{ margin: 0 }}>Focus: Equivalent fractions · CCSS 4.NF.A.1</p>
        <Link to="/teacher/activities" className="btn btn-primary" style={{ textDecoration: 'none' }}>Assign a quest</Link>
      </div>

      <div className="grid-3">
        <div className="card tinted-cream"><div className="stat">{data.counts.needs_more_evidence + without.length}</div><div className="stat-label">learners need more evidence</div></div>
        <div className="card tinted-mint"><div className="stat">{data.counts.ready_for_extension}</div><div className="stat-label">learners are ready for extension</div></div>
        <div className="card tinted-sky"><div className="stat">{data.students.length - without.length}<span style={{ fontSize: '0.5em', opacity: 0.7 }}>/{data.students.length}</span></div><div className="stat-label">have practice evidence</div></div>
      </div>

      <div className="card">
        <div className="row between" style={{ marginBottom: 8 }}><h2 style={{ margin: 0 }}>Learners</h2><span className="muted">Neutral language by design. No rankings.</span></div>
        <table>
          <thead><tr><th>Learner</th><th>Skill</th><th>Where they are</th><th>Mastery</th><th>Confidence</th><th>Quests done</th><th></th></tr></thead>
          <tbody>
            {data.mastery.map((m) => (
              <tr key={m.student_id + m.skill_name}>
                <td className="learner-cell">
                  <Avatar photo={face(m.student_id)?.photo} spec={face(m.student_id)?.avatar} size={36} />
                  {m.display_name}
                  {m.has_goal_link && <span className="chip" title="You linked this learner's evidence to a plain-language IEP/504 goal label. Only you see this marker." style={{ marginLeft: 6 }}>🔗 goal link</span>}
                </td>
                <td className="muted">{m.skill_name}</td>
                <td><span className={`chip ${BAND_TONE[m.band]}`}>{m.band}</span></td>
                <td><span className="bar" aria-hidden="true"><i style={{ width: `${Math.round(m.estimate * 100)}%` }} /></span> <span className="muted">{Math.round(m.estimate * 100)}%</span></td>
                <td><span className={`chip ${CONF_TONE[m.confidence]}`}>{m.confidence}</span></td>
                <td>{m.quests_done} quest{m.quests_done === 1 ? '' : 's'}</td>
                <td><button type="button" className="table-btn" onClick={() => api<Evidence>(`/teacher/students/${m.student_id}`).then(setOpen)}>Details</button></td>
              </tr>
            ))}
            {without.map((s) => (
              <tr key={s.id}>
                <td className="learner-cell">
                  <Avatar photo={s.photo} spec={s.avatar} size={36} />{s.display_name}
                </td>
                <td colSpan={5} className="muted">No practice evidence yet</td><td></td>
              </tr>
            ))}
          </tbody>
        </table>
        <p className="muted table-note">
          <strong>Mastery</strong> is our best estimate that the learner knows this skill right now, based on
          their answers so far. <strong>🔗 goal link</strong> means you connected this learner's evidence
          to a plain-language goal label you wrote; learners and other families never see it. <strong>Quests done</strong> counts
          finished quests on that skill.
        </p>
      </div>

      {open && (
        <div className="card" role="region" aria-label="Item evidence">
          <div className="row between"><h2 style={{ margin: 0 }}>Details for {openName}</h2><button type="button" onClick={() => setOpen(null)}>Close</button></div>
          {open.evidence.length === 0 ? <p className="muted" style={{ marginTop: 12 }}>No answers yet. Ask the learner to try a quest.</p> : (
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


      <div className="card" style={{ background: 'var(--surface-2)' }}>
        <strong>How this works.</strong> <span className="muted">After every answer we update one number per skill: how likely it is that this learner knows it. Items are calibrated so the model knows which questions are hard, and the next question is the one that tells us the most without being discouraging. Nothing here diagnoses, grades, or places a student.</span>
      </div>
    </div>
  )
}
