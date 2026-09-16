// Learners tab: the class at a glance, then one card per child. A table of skill rows made a
// class look like a spreadsheet; twelve faces look like twelve children, and the detail a
// teacher actually reads lives one click away on the learner's own page.

import { useEffect, useState } from 'react'
import { Link } from 'react-router-dom'
import { api } from '../api'
import Avatar, { type AvatarSpec } from '../components/Avatar'

interface Row {
  student_id: string; display_name: string; has_goal_link: boolean; skill_name: string
  band: string; estimate: number; confidence: string; evidence_count: number; quests_done: number
}
interface Learner { id: string; display_name: string; photo?: string | null; avatar?: AvatarSpec | null }
interface ClassStats { checkins: number; quests_done: number; active_learners: number; avg_estimate: number | null }
interface Summary {
  class_id: string; students: Learner[]; mastery: Row[]
  counts: { needs_more_evidence: number; ready_for_extension: number }
  class_stats: ClassStats
}

const BAND_TONE: Record<string, string> = { 'Building foundations': 'cream', Practicing: 'sky', 'Ready for extension': 'mint' }

/** One learner's headline: the skill they are furthest from, because that is the one to act on. */
function focusOf(rows: Row[]) {
  if (rows.length === 0) return null
  return rows.reduce((lowest, row) => (row.estimate < lowest.estimate ? row : lowest))
}

export default function TeacherDashboard() {
  const [data, setData] = useState<Summary | null>(null)
  const [err, setErr] = useState<string | null>(null)

  useEffect(() => { api<Summary>('/teacher/class').then(setData).catch((e) => setErr(String(e))) }, [])

  if (err) return <p role="alert">{err}</p>
  if (!data) return <p>Loading…</p>

  const withEvidence = new Set(data.mastery.map((m) => m.student_id))
  const needsEvidence = data.counts.needs_more_evidence + (data.students.length - withEvidence.size)

  const SUMMARY = [
    { value: data.students.length, label: 'learners in this class', tone: 'tinted-sky' },
    { value: needsEvidence, label: 'need more evidence before you can act', tone: 'tinted-cream' },
    { value: data.counts.ready_for_extension, label: 'are ready for extension', tone: 'tinted-mint' },
    // Answers behind the evidence, not attempts logged: seeded learners arrive with mastery
    // history and no item log, and a zero here would read as "nobody has done anything".
    { value: data.mastery.reduce((total, row) => total + row.evidence_count, 0),
      label: 'answers behind this evidence', tone: '' },
  ]

  return (
    <div className="stack">
      <div className="row between">
        <p className="muted" style={{ margin: 0 }}>Focus: Equivalent fractions · CCSS 4.NF.A.1</p>
        <Link to="/teacher/activities" className="btn btn-primary" style={{ textDecoration: 'none' }}>Assign a quest</Link>
      </div>

      <section aria-label="Class summary" className="class-summary">
        {SUMMARY.map((tile) => (
          <div className={`card ${tile.tone}`} key={tile.label}>
            <div className="stat">{tile.value}</div>
            <div className="stat-label">{tile.label}</div>
          </div>
        ))}
      </section>

      <section aria-labelledby="roster-title">
        <div className="row between" style={{ marginBottom: 12 }}>
          <h2 id="roster-title" style={{ margin: 0 }}>Learners</h2>
          <span className="muted">Neutral language by design. No rankings, no ordering by score.</span>
        </div>

        <ul className="learner-grid">
          {data.students.map((student) => {
            const rows = data.mastery.filter((m) => m.student_id === student.id)
            const focus = focusOf(rows)
            const goalLink = rows.some((r) => r.has_goal_link)
            return (
              <li key={student.id}>
                <Link className="learner-card" to={`/teacher/learners/${student.id}`}>
                  <Avatar photo={student.photo} spec={student.avatar} size={84} />
                  <strong className="learner-name">{student.display_name}</strong>
                  {focus ? (
                    <>
                      <span className={`chip ${BAND_TONE[focus.band] ?? ''}`}>{focus.band}</span>
                      <span className="learner-focus muted">{focus.skill_name}</span>
                    </>
                  ) : (
                    <span className="chip">No evidence yet</span>
                  )}
                  <span className="learner-meta muted">
                    {rows.length} skill{rows.length === 1 ? '' : 's'} with evidence
                    {goalLink && <span className="goal-dot" title="Has a goal link (only you see this)" aria-label="Has a goal link">🔗</span>}
                  </span>
                </Link>
              </li>
            )
          })}
        </ul>
      </section>

      <div className="card" style={{ background: 'var(--surface-2)' }}>
        <strong>How this works.</strong> <span className="muted">After every answer we update one number per skill: how likely it is that this learner knows it. Items are calibrated so the model knows which questions are hard, and the next question is the one that tells us the most without being discouraging. Nothing here diagnoses, grades, or places a student.</span>
      </div>
    </div>
  )
}
