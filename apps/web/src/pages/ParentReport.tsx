// A summary a family can take to their child's doctor.
//
// Two rules shape this page, both from docs/GUIDELINES.md §8:
//
// - **Show it before you share it.** The family sees the whole document on screen first.
//   Nothing is assembled out of sight and handed over sealed; a parent should never wonder
//   what they just sent to a clinic about their child.
// - **The family does the sending.** There is no email button and no upload. The page
//   produces a file on their own machine, and what happens to it afterwards is their call.
//   A product that mails a child's learning record to a clinic needs a consent flow this
//   one does not have.
//
// The disclaimer is rendered from the server's payload rather than written here, so a
// change to the boundary text cannot be lost by a front end that forgets to update.

import { useEffect, useState } from 'react'
import { api } from '../api'

interface SkillRow {
  subject: string; skill: string; in_plain_words: string; standard: string
  where_they_are: string; practice_behind_it: string
  questions_answered: number; direction: string
}
interface NextStep {
  title: string; why: string; minutes: number | null
  approved_by: string; approved_on: string
}
interface Report {
  child: { name: string; grade: number | null }
  generated_on: string
  covers: { first_activity: string | null; last_activity: string | null; days_active: number }
  practice: { questions_answered: number; answered_correctly: number; hints_opened: number; quests_finished: number }
  skills: SkillRow[]
  teacher_approved_next_steps: NextStep[]
  supports_used_in_the_app: string[]
  what_this_is_not: string
  prepared_by: string
}
interface Child { id: string; display_name: string }

function longDate(iso: string | null) {
  if (!iso) return '—'
  const [y, m, d] = iso.split('-').map(Number)
  return new Date(y, m - 1, d).toLocaleDateString(undefined, { year: 'numeric', month: 'long', day: 'numeric' })
}

/** The document as plain text, which is what actually gets saved and attached. */
function asText(r: Report) {
  const line = '='.repeat(64)
  const out: string[] = [
    `LEARNING PRACTICE SUMMARY — ${r.child.name}`,
    line,
    `Prepared by: ${r.prepared_by}`,
    `Prepared on: ${longDate(r.generated_on)}`,
    r.child.grade ? `Grade: ${r.child.grade}` : '',
    `Covers: ${longDate(r.covers.first_activity)} to ${longDate(r.covers.last_activity)}`
      + ` (${r.covers.days_active} days with activity)`,
    '',
    'PLEASE READ FIRST',
    '-'.repeat(64),
    r.what_this_is_not,
    '',
    'PRACTICE IN THIS PERIOD',
    '-'.repeat(64),
    `Questions answered:   ${r.practice.questions_answered}`,
    `Answered correctly:   ${r.practice.answered_correctly}`,
    `Hints opened:         ${r.practice.hints_opened}`,
    `Practice sets finished: ${r.practice.quests_finished}`,
    '',
    'SKILLS PRACTISED',
    '-'.repeat(64),
  ]
  for (const s of r.skills) {
    out.push(`${s.subject.toUpperCase()} — ${s.skill}${s.standard ? ` (${s.standard})` : ''}`)
    if (s.in_plain_words) out.push(`  In plain words: ${s.in_plain_words}`)
    out.push(`  ${s.where_they_are}`)
    out.push(`  ${s.practice_behind_it} — ${s.questions_answered} questions, ${s.direction}.`)
    out.push('')
  }
  if (r.teacher_approved_next_steps.length) {
    out.push('NEXT STEPS THE TEACHER APPROVED', '-'.repeat(64))
    for (const n of r.teacher_approved_next_steps) {
      out.push(`${n.title}${n.minutes ? ` (${n.minutes} minutes)` : ''}`)
      if (n.why) out.push(`  Why: ${n.why}`)
      if (n.approved_by) out.push(`  Approved by ${n.approved_by}${n.approved_on ? ` on ${longDate(n.approved_on)}` : ''}`)
      out.push('')
    }
  }
  if (r.supports_used_in_the_app.length) {
    out.push('SETTINGS THIS CHILD USES IN THE APP', '-'.repeat(64))
    out.push('These are app settings available to every learner, not findings about this child.')
    for (const s of r.supports_used_in_the_app) out.push(`  - ${s}`)
    out.push('')
  }
  out.push(line, r.what_this_is_not)
  return out.filter((l) => l !== undefined).join('\n')
}

export default function ParentReport() {
  const [children, setChildren] = useState<Child[]>([])
  const [childId, setChildId] = useState('')
  const [report, setReport] = useState<Report | null>(null)
  const [error, setError] = useState('')

  useEffect(() => {
    api<Child[]>('/parent/children')
      .then((rows) => { setChildren(rows); setChildId(rows[0]?.id ?? '') })
      .catch(() => setError('Your children could not load.'))
  }, [])

  useEffect(() => {
    if (!childId) return
    setReport(null)
    api<Report>(`/parent/children/${childId}/report`)
      .then(setReport)
      .catch(() => setError('That summary could not load.'))
  }, [childId])

  function download() {
    if (!report) return
    const blob = new Blob([asText(report)], { type: 'text/plain;charset=utf-8' })
    const url = URL.createObjectURL(blob)
    const link = document.createElement('a')
    link.href = url
    link.download = `${report.child.name}-learning-summary-${report.generated_on}.txt`
    document.body.appendChild(link)
    link.click()
    link.remove()
    URL.revokeObjectURL(url)
  }

  if (error) return <p role="alert">{error}</p>

  return (
    <div className="stack">
      <section className="card no-print" aria-labelledby="export-title">
        <h2 id="export-title" style={{ marginTop: 0 }}>Share a summary with your child's doctor</h2>
        <p className="muted" style={{ maxWidth: '62ch' }}>
          Appointments often start with "what does the school say?". This puts what your child
          has been practising in one place, in plain words, so you have something to bring.
          Everything in it is shown below before you save it — nothing is sent anywhere by us,
          and who sees it is entirely your decision.
        </p>

        <div className="report-controls">
          {children.length > 1 && (
            <label className="msg-field">
              <span>Which child?</span>
              <select value={childId} onChange={(event) => setChildId(event.target.value)}>
                {children.map((child) => (
                  <option key={child.id} value={child.id}>{child.display_name}</option>
                ))}
              </select>
            </label>
          )}
          <div className="row">
            <button type="button" className="btn-primary btn-lg" disabled={!report} onClick={download}>
              Save as a file
            </button>
            <button type="button" className="btn-lg" disabled={!report} onClick={() => window.print()}>
              Print or save as PDF
            </button>
          </div>
        </div>
      </section>

      {!report ? <p>Preparing the summary…</p> : (
        <article className="card report-sheet">
          <header className="report-head">
            <h2>Learning practice summary</h2>
            <p className="report-for"><strong>{report.child.name}</strong>
              {report.child.grade ? ` · Grade ${report.child.grade}` : ''}</p>
            <p className="muted">
              Prepared {longDate(report.generated_on)} by {report.prepared_by}<br />
              Covers {longDate(report.covers.first_activity)} to {longDate(report.covers.last_activity)}
              {' '}· {report.covers.days_active} days with activity
            </p>
          </header>

          {/* First thing on the page and first thing in the file. */}
          <div className="report-note" role="note">
            <strong>Please read first.</strong> {report.what_this_is_not}
          </div>

          <h3>Practice in this period</h3>
          <div className="report-figures">
            <div><b>{report.practice.questions_answered}</b><span>questions answered</span></div>
            <div><b>{report.practice.answered_correctly}</b><span>answered correctly</span></div>
            <div><b>{report.practice.quests_finished}</b><span>practice sets finished</span></div>
            <div><b>{report.practice.hints_opened}</b><span>hints opened</span></div>
          </div>

          <h3>Skills practised</h3>
          <table className="report-table">
            <thead>
              <tr>
                <th scope="col">Skill</th><th scope="col">Where they are</th>
                <th scope="col">Practice behind it</th><th scope="col">Direction</th>
              </tr>
            </thead>
            <tbody>
              {report.skills.map((s) => (
                <tr key={`${s.subject}-${s.skill}`}>
                  <td>
                    <b>{s.skill}</b>
                    <span className="muted report-sub">
                      {s.subject}{s.standard ? ` · ${s.standard}` : ''}
                      {s.in_plain_words ? <><br />{s.in_plain_words}</> : null}
                    </span>
                  </td>
                  <td>{s.where_they_are}</td>
                  <td>{s.practice_behind_it}<span className="muted report-sub"><br />
                    {s.questions_answered} question{s.questions_answered === 1 ? '' : 's'}</span></td>
                  <td>{s.direction}</td>
                </tr>
              ))}
            </tbody>
          </table>

          {report.teacher_approved_next_steps.length > 0 && (
            <>
              <h3>Next steps the teacher approved</h3>
              <ul className="report-steps">
                {report.teacher_approved_next_steps.map((n) => (
                  <li key={n.title}>
                    <b>{n.title}</b>{n.minutes ? ` · ${n.minutes} minutes` : ''}
                    {n.why && <><br /><span className="muted">{n.why}</span></>}
                    {n.approved_by && <><br /><span className="muted">
                      Approved by {n.approved_by}{n.approved_on ? ` on ${longDate(n.approved_on)}` : ''}
                    </span></>}
                  </li>
                ))}
              </ul>
            </>
          )}

          {report.supports_used_in_the_app.length > 0 && (
            <>
              <h3>Settings this child uses in the app</h3>
              <p className="muted">
                These are settings any learner can turn on. They are listed because you may want
                to mention them, not as findings about your child.
              </p>
              <ul>{report.supports_used_in_the_app.map((s) => <li key={s}>{s}</li>)}</ul>
            </>
          )}

          <footer className="report-foot muted">{report.what_this_is_not}</footer>
        </article>
      )}
    </div>
  )
}
