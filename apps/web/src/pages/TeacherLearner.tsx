// One learner's page: who they are, where they are on each skill, and the item-level evidence
// behind every claim. This is the screen a teacher reads before a meeting, so nothing here is
// a summary you have to take on trust — every band traces back to answers you can see.

import { useEffect, useState } from 'react'
import { Link, useParams } from 'react-router-dom'
import { api } from '../api'
import Avatar, { type AvatarSpec } from '../components/Avatar'
import RecommendationPanel from '../components/RecommendationPanel'

interface Skill {
  skill_id: string; skill_name: string; subject: string; standard_id: string
  estimate: number; band: string; confidence: string; evidence_count: number; history: number[]
}
interface EvidenceRow {
  at: string; prompt: string; difficulty: number | null; skill_name: string
  correct: boolean; hint_used: boolean; route_reason?: string | null
}
interface Detail {
  student: { id: string; display_name: string; grade: number; has_goal_link: boolean; photo?: string | null; avatar?: AvatarSpec | null }
  totals: { questions: number; quests_done: number; hints: number; skills_with_evidence: number }
  mastery: Skill[]
  evidence: EvidenceRow[]
  group_activities: { id: string; title: string; group_name: string; teammates: string[] }[]
}

const BAND_TONE: Record<string, string> = { 'Building foundations': 'cream', Practicing: 'sky', 'Ready for extension': 'mint' }
const CONF_TONE: Record<string, string> = { low: 'rose', medium: 'cream', high: 'mint' }

/** The mastery estimate over time. Drawn, but the numbers are in the text beside it. */
function Trend({ history }: { history: number[] }) {
  if (history.length < 2) return null
  const points = history.map((value, index) => {
    const x = (index / (history.length - 1)) * 100
    return `${x},${28 - value * 26}`
  }).join(' ')
  return (
    <svg className="trend" viewBox="0 0 100 30" preserveAspectRatio="none" aria-hidden="true">
      <polyline points={points} fill="none" stroke="currentColor" strokeWidth="2.5"
        strokeLinecap="round" strokeLinejoin="round" vectorEffect="non-scaling-stroke" />
    </svg>
  )
}

export default function TeacherLearner() {
  const { studentId = '' } = useParams()
  const [data, setData] = useState<Detail | null>(null)
  const [err, setErr] = useState('')

  useEffect(() => {
    setData(null)
    api<Detail>(`/teacher/students/${studentId}`)
      .then(setData)
      .catch(() => setErr('That learner could not be loaded.'))
  }, [studentId])

  if (err) return <p role="alert">{err} <Link to="/teacher">Back to learners</Link></p>
  if (!data) return <p>Loading…</p>

  const { student, totals, mastery, evidence, group_activities: groups } = data
  const TOTALS = [
    { value: totals.questions, label: 'questions answered' },
    { value: totals.quests_done, label: 'quests finished' },
    { value: totals.skills_with_evidence, label: 'skills with evidence' },
    { value: totals.hints, label: 'hints used' },
  ]

  return (
    <div className="stack">
      <Link to="/teacher" className="btn-ghost back-link">← All learners</Link>

      <section className="card learner-head">
        <Avatar photo={student.photo} spec={student.avatar} size={96} name={student.display_name} />
        <div>
          <h2 style={{ margin: 0 }}>{student.display_name}</h2>
          <p className="muted" style={{ margin: '2px 0 0' }}>Grade {student.grade}</p>
          {student.has_goal_link && (
            <span className="chip" style={{ marginTop: 8 }}
              title="You linked this learner's evidence to a plain-language IEP/504 goal label. Only you see this marker.">
              🔗 goal link
            </span>
          )}
        </div>
        <dl className="learner-totals">
          {TOTALS.map((t) => (
            <div key={t.label}><dt>{t.value}</dt><dd>{t.label}</dd></div>
          ))}
        </dl>
      </section>

      <section aria-labelledby="skills-title">
        <h3 id="skills-title" style={{ marginBottom: 10 }}>Where {student.display_name} is right now</h3>
        {mastery.length === 0 ? (
          <div className="card"><p className="muted" style={{ margin: 0 }}>
            No practice evidence yet. Assign a quest and this fills in after the first answers.
          </p></div>
        ) : (
          <div className="skill-grid">
            {mastery.map((skill) => (
              <article className="card skill-card" key={skill.skill_id}>
                <div className="row between">
                  <div>
                    <strong>{skill.skill_name}</strong>
                    <p className="muted" style={{ margin: 0, fontSize: '.86em' }}>
                      {skill.subject}{skill.standard_id ? ` · ${skill.standard_id}` : ''}
                    </p>
                  </div>
                  <span className={`chip ${BAND_TONE[skill.band] ?? ''}`}>{skill.band}</span>
                </div>
                <div className="skill-measure">
                  <span className="bar" aria-hidden="true"><i style={{ width: `${Math.round(skill.estimate * 100)}%` }} /></span>
                  <strong>{Math.round(skill.estimate * 100)}%</strong>
                  <Trend history={skill.history} />
                </div>
                {/* The separator is dropped rather than left to start a wrapped line. */}
                <p className="muted skill-foot">
                  <span>Confidence <span className={`chip ${CONF_TONE[skill.confidence]}`}>{skill.confidence}</span></span>
                  <span>{skill.evidence_count} answer{skill.evidence_count === 1 ? '' : 's'} behind this</span>
                </p>
              </article>
            ))}
          </div>
        )}
      </section>

      <RecommendationPanel studentId={student.id}
        skills={mastery.map((m) => ({ skill_id: m.skill_id, skill_name: m.skill_name }))} />

      {groups.length > 0 && (
        <section className="card">
          <h3 style={{ marginTop: 0 }}>Working with</h3>
          <ul className="plain-list">
            {groups.map((g) => (
              <li key={g.id}>
                <strong>{g.title}</strong> · {g.group_name}
                <span className="muted"> with {g.teammates.join(' and ')}</span>
              </li>
            ))}
          </ul>
        </section>
      )}

      <section className="card" aria-labelledby="evidence-title">
        <div className="row between">
          <h3 id="evidence-title" style={{ margin: 0 }}>Every answer, newest first</h3>
          <span className="muted">{evidence.length} recorded</span>
        </div>
        {evidence.length === 0 ? (
          <p className="muted" style={{ marginTop: 12 }}>No answers yet. Ask {student.display_name} to try a quest.</p>
        ) : (
          <div className="table-scroll">
            <table style={{ marginTop: 12 }}>
              <thead><tr><th>Question</th><th>Skill</th><th>Difficulty</th><th>Result</th><th>Hint</th><th>Note</th></tr></thead>
              <tbody>
                {evidence.map((e, i) => (
                  <tr key={i}>
                    <td>{e.prompt}</td>
                    <td className="muted">{e.skill_name}</td>
                    <td>{e.difficulty ?? ''}</td>
                    <td><span className={`chip ${e.correct ? 'mint' : 'sky'}`}>{e.correct ? 'correct' : 'not yet'}</span></td>
                    <td>{e.hint_used ? '💡 used' : ''}</td>
                    <td className="muted">{e.route_reason ?? ''}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </section>
    </div>
  )
}
