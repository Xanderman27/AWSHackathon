// The teacher-family loop around one child: guardian contacts, the support plan (IEP or
// 504), shared goals, and the family's requests to update the plan.
//
// The rules mirror real life. A family never edits an IEP directly - changes go through
// the team - so families SUGGEST updates and the teacher records the decision. Goals a
// teacher writes are active at once; goals a family proposes wait for approval.

import { useCallback, useEffect, useState, type FormEvent } from 'react'
import { api, getSession } from '../api'
import { composeMessageFor } from './MessagesWidget'

export interface Plan {
  id: string; student_id: string; type: 'IEP' | '504'; status: string
  adopted_on: string; annual_review: string; reevaluation_due: string
  case_manager: string; team: string[]; eligibility: string; present_levels: string
  plan_goals: string[]; accommodations: string[]; services: string[]
  amendments: { text: string; by: string; role: string; at: string }[]
  note: string
}
export interface Goal {
  id: string; student_id: string; title: string; why: string
  status: 'proposed' | 'active' | 'declined' | 'met'
  created_by: string; created_by_name: string; created_by_role: string
  at: string; decided_by: string | null
  progress_note?: string; progress_noted_on?: string
}

/** What the agent came back with, before a teacher has decided to send it. */
interface NoteDraft {
  statement: string
  evidence_cited: string[]
  sufficiency: 'enough' | 'thin'
  origin: string
  looked_at: string[]
  turns: number
  warning: string
}
export interface PlanRequest {
  id: string; student_id: string; text: string
  status: 'proposed' | 'accepted' | 'declined'
  by: string; by_name: string; at: string; decided_by: string | null
}
export interface Guardian {
  id: string; display_name: string; relation: string; email: string; phone: string
}
export interface SupportData {
  plan: Plan | null; goals: Goal[]; plan_requests: PlanRequest[]; guardians: Guardian[]
}

export function useSupport(studentId: string) {
  const [data, setData] = useState<SupportData | null>(null)
  const reload = useCallback(() => {
    api<SupportData>(`/support/students/${studentId}`).then(setData).catch(() => setData(null))
  }, [studentId])
  useEffect(() => { setData(null); reload() }, [reload])
  return { data, reload }
}

const GOAL_TONE: Record<Goal['status'], string> = {
  proposed: 'cream', active: 'sky', met: 'mint', declined: '',
}
const GOAL_WORD: Record<Goal['status'], string> = {
  proposed: 'waiting for teacher', active: 'working on it', met: 'met!', declined: 'not this time',
}

/** The plan document itself, shared by the teacher and family views. */
export function PlanDoc({ plan }: { plan: Plan }) {
  return (
    <div className="plan-doc">
      <div className="plan-facts">
        <span className={`chip ${plan.type === 'IEP' ? 'sky' : 'cream'}`}>{plan.type === 'IEP' ? 'IEP' : '504 Plan'}</span>
        <span className="chip mint">{plan.status}</span>
        <span className="muted">Adopted {plan.adopted_on} · Annual review {plan.annual_review} · Re-evaluation {plan.reevaluation_due}</span>
      </div>
      <p className="muted plan-team">Case manager {plan.case_manager} · Team: {plan.team.join(', ')}</p>

      <details open>
        <summary>Present levels</summary>
        <p>{plan.present_levels}</p>
        <p className="muted" style={{ fontSize: '.86em' }}>Basis: {plan.eligibility}</p>
      </details>
      {plan.plan_goals.length > 0 && (
        <details>
          <summary>Annual goals</summary>
          <ul>{plan.plan_goals.map((g, i) => <li key={i}>{g}</li>)}</ul>
        </details>
      )}
      <details>
        <summary>Accommodations</summary>
        <ul>{plan.accommodations.map((a, i) => <li key={i}>{a}</li>)}</ul>
      </details>
      <details>
        <summary>Services</summary>
        {plan.services.length === 0 ? <p className="muted">None on file.</p>
          : <ul>{plan.services.map((s, i) => <li key={i}>{s}</li>)}</ul>}
      </details>
      <details open={plan.amendments.length > 0}>
        <summary>Updates and amendments</summary>
        {plan.amendments.length === 0 ? <p className="muted">No amendments yet.</p> : (
          <ul>
            {plan.amendments.map((a, i) => (
              <li key={i}>{a.text} <span className="muted">— {a.by}, {a.at}</span></li>
            ))}
          </ul>
        )}
      </details>
      <p className="note" style={{ fontSize: '.82em' }}>{plan.note}</p>
    </div>
  )
}

/** Draft, edit and send the periodic progress note for one goal (FR-25).
 *
 * IDEA asks for periodic reports on progress toward annual goals. The teacher stays the
 * author: the agent assembles the evidence and proposes wording, and nothing reaches the
 * family until the teacher has read it and pressed send.
 */
function ProgressNote({ goal, onSent }: { goal: Goal; onSent: () => void }) {
  const [draft, setDraft] = useState<NoteDraft | null>(null)
  const [text, setText] = useState('')
  const [busy, setBusy] = useState(false)
  const [err, setErr] = useState('')

  async function makeDraft() {
    setBusy(true); setErr('')
    try {
      const made = await api<NoteDraft>(`/support/goals/${goal.id}/progress-note/draft`, { method: 'POST' })
      setDraft(made)
      setText(made.statement)
    } catch {
      setErr('The draft could not be written. You can still write the note yourself.')
    } finally { setBusy(false) }
  }

  async function send() {
    setBusy(true); setErr('')
    try {
      await api(`/support/goals/${goal.id}/progress-note`, {
        method: 'POST', body: JSON.stringify({ statement: text }),
      })
      setDraft(null)
      onSent()
    } catch {
      setErr('That note could not be sent.')
    } finally { setBusy(false) }
  }

  if (goal.progress_note && !draft) {
    return (
      <div className="progress-note sent">
        <p className="muted note-label">Progress note sent to the family</p>
        <p className="note-body">{goal.progress_note}</p>
        <button type="button" disabled={busy} onClick={makeDraft}>
          {busy ? 'Drafting…' : 'Draft a new one'}
        </button>
      </div>
    )
  }

  if (!draft) {
    return (
      <div className="row" style={{ marginTop: 8 }}>
        <button type="button" disabled={busy} onClick={makeDraft}
          title="An agent gathers the evidence behind this goal and proposes the wording">
          {busy ? 'Gathering the evidence…' : 'Draft progress note'}
        </button>
        {err && <span className="muted" role="alert">{err}</span>}
      </div>
    )
  }

  return (
    <div className="progress-note">
      <div className="row between">
        <p className="muted note-label">Draft for the family — your words before it sends</p>
        <span className={`chip ${draft.sufficiency === 'enough' ? 'mint' : 'cream'}`}>
          {draft.sufficiency === 'enough' ? 'evidence supports this' : 'evidence is thin'}
        </span>
      </div>
      <textarea value={text} rows={4} maxLength={900} onChange={(e) => setText(e.target.value)} />
      <p className="agent-trace muted">
        {draft.origin === 'bedrock'
          ? `agent read ${draft.looked_at.join(', ')} · ${draft.turns} steps`
          : draft.warning}
      </p>
      <div className="row">
        <button type="button" className="btn-primary" disabled={busy || text.trim().length < 20} onClick={send}>
          {busy ? 'Sending…' : 'Send to the family'}
        </button>
        <button type="button" disabled={busy} onClick={() => setDraft(null)}>Discard</button>
      </div>
      {err && <p className="muted" role="alert">{err}</p>}
    </div>
  )
}

export function GoalList({ goals, canDecide, onDecide, onChanged }: {
  goals: Goal[]
  canDecide: boolean
  onDecide?: (id: string, action: 'approve' | 'decline' | 'complete') => void
  onChanged?: () => void
}) {
  if (goals.length === 0) return <p className="muted" style={{ margin: 0 }}>No shared goals yet.</p>
  return (
    <ul className="plain-list goal-list">
      {goals.map((goal) => (
        <li key={goal.id} className={`goal ${goal.status}`}>
          <div className="row between" style={{ alignItems: 'start' }}>
            <div>
              <strong>{goal.title}</strong>
              {goal.why && <p className="muted" style={{ margin: '2px 0 0', fontSize: '.9em' }}>{goal.why}</p>}
              <p className="muted" style={{ margin: '4px 0 0', fontSize: '.82em' }}>
                {goal.created_by_role === 'teacher' ? 'Set by' : 'Suggested by'} {goal.created_by_name}
              </p>
            </div>
            <span className={`chip ${GOAL_TONE[goal.status]}`}>{GOAL_WORD[goal.status]}</span>
          </div>
          {canDecide && onDecide && goal.status === 'proposed' && (
            <div className="row" style={{ gap: 8, marginTop: 8 }}>
              <button type="button" className="btn-primary" onClick={() => onDecide(goal.id, 'approve')}>Approve</button>
              <button type="button" onClick={() => onDecide(goal.id, 'decline')}>Not now</button>
            </div>
          )}
          {canDecide && onDecide && goal.status === 'active' && (
            <div className="row" style={{ marginTop: 8 }}>
              <button type="button" onClick={() => onDecide(goal.id, 'complete')}>Mark met 🎉</button>
            </div>
          )}
          {canDecide && goal.status === 'active' && (
            <ProgressNote goal={goal} onSent={() => onChanged?.()} />
          )}
          {!canDecide && goal.progress_note && (
            <div className="progress-note sent">
              <p className="muted note-label">From {goal.created_by_name}</p>
              <p className="note-body">{goal.progress_note}</p>
            </div>
          )}
        </li>
      ))}
    </ul>
  )
}

export function GoalForm({ studentId, role, onSaved }: {
  studentId: string; role: 'teacher' | 'parent'; onSaved: () => void
}) {
  const [title, setTitle] = useState('')
  const [why, setWhy] = useState('')
  const [busy, setBusy] = useState(false)

  async function submit(e: FormEvent) {
    e.preventDefault()
    if (!title.trim() || busy) return
    setBusy(true)
    try {
      await api(`/support/students/${studentId}/goals`, {
        method: 'POST', body: JSON.stringify({ title, why }),
      })
      setTitle(''); setWhy(''); onSaved()
    } finally { setBusy(false) }
  }

  return (
    <form className="goal-form" onSubmit={submit}>
      <input type="text" value={title} maxLength={140} placeholder={role === 'teacher' ? 'New goal…' : 'Suggest a goal…'}
        onChange={(e) => setTitle(e.target.value)} aria-label="Goal title" />
      <input type="text" value={why} maxLength={600} placeholder="Why it matters (optional)"
        onChange={(e) => setWhy(e.target.value)} aria-label="Why this goal matters" />
      <button type="submit" className="btn-primary" disabled={busy || !title.trim()}>
        {role === 'teacher' ? 'Add goal' : 'Send to teacher'}
      </button>
      {role === 'parent' && (
        <p className="muted" style={{ margin: 0, fontSize: '.82em', gridColumn: '1 / -1' }}>
          The teacher reviews every suggestion before it becomes a working goal.
        </p>
      )}
    </form>
  )
}

/* ---------------- Teacher side ---------------- */

export function TeacherSupport({ studentId, studentName }: { studentId: string; studentName: string }) {
  const { data, reload } = useSupport(studentId)
  if (!data) return null
  const pending = data.plan_requests.filter((r) => r.status === 'proposed')
  const decidedRequests = data.plan_requests.filter((r) => r.status !== 'proposed')

  const decideGoal = (id: string, action: string) =>
    api(`/support/goals/${id}/decide`, { method: 'POST', body: JSON.stringify({ action }) }).then(reload)
  const decideRequest = (id: string, action: string) =>
    api(`/support/plan-requests/${id}/decide`, { method: 'POST', body: JSON.stringify({ action }) }).then(reload)

  return (
    <>
      <section className="card" aria-labelledby="family-title">
        <h3 id="family-title" style={{ marginTop: 0 }}>Family</h3>
        {data.guardians.length === 0 ? (
          <p className="muted" style={{ margin: 0 }}>No family account is linked yet.</p>
        ) : (
          <ul className="plain-list">
            {data.guardians.map((g) => (
              <li key={g.id} className="guardian-row">
                <div>
                  <strong>{g.display_name}</strong> <span className="chip">{g.relation}</span>
                  <p className="muted" style={{ margin: '2px 0 0', fontSize: '.9em' }}>
                    <a href={`mailto:${g.email}`}>{g.email}</a> · {g.phone}
                  </p>
                </div>
                <button type="button" className="btn-primary" onClick={() => composeMessageFor(studentId)}>
                  💬 Message
                </button>
              </li>
            ))}
          </ul>
        )}
      </section>

      <section className="card" aria-labelledby="plan-title">
        <h3 id="plan-title" style={{ marginTop: 0 }}>Support plan</h3>
        {!data.plan ? (
          <p className="muted" style={{ margin: 0 }}>No IEP or 504 plan on file for {studentName}.</p>
        ) : (
          <>
            {pending.length > 0 && (
              <div className="plan-requests" role="region" aria-label="Family requests waiting for you">
                {pending.map((r) => (
                  <div className="feedback try plan-request" key={r.id}>
                    <div>
                      <strong>{r.by_name} suggests:</strong> {r.text}
                    </div>
                    <div className="row" style={{ gap: 8 }}>
                      <button type="button" className="btn-primary" onClick={() => decideRequest(r.id, 'approve')}>
                        Agree &amp; add to plan
                      </button>
                      <button type="button" onClick={() => decideRequest(r.id, 'decline')}>Decline</button>
                    </div>
                  </div>
                ))}
              </div>
            )}
            <PlanDoc plan={data.plan} />
            {decidedRequests.length > 0 && (
              <p className="muted" style={{ fontSize: '.85em' }}>
                Past family requests: {decidedRequests.map((r) => `"${r.text.slice(0, 40)}…" (${r.status})`).join(' · ')}
              </p>
            )}
          </>
        )}
      </section>

      <section className="card" aria-labelledby="goals-title">
        <h3 id="goals-title" style={{ marginTop: 0 }}>Goals with the family</h3>
        <GoalList goals={data.goals} canDecide onDecide={decideGoal} onChanged={reload} />
        <GoalForm studentId={studentId} role="teacher" onSaved={reload} />
      </section>
    </>
  )
}

/* ---------------- Family side ---------------- */

export function FamilySupport({ studentId, studentName }: { studentId: string; studentName: string }) {
  const { data, reload } = useSupport(studentId)
  const [suggestion, setSuggestion] = useState('')
  const [busy, setBusy] = useState(false)
  const role = getSession()?.role
  if (!data || role !== 'parent') return null

  async function suggest(e: FormEvent) {
    e.preventDefault()
    if (!suggestion.trim() || busy) return
    setBusy(true)
    try {
      await api(`/support/students/${studentId}/plan-requests`, {
        method: 'POST', body: JSON.stringify({ text: suggestion }),
      })
      setSuggestion(''); reload()
    } finally { setBusy(false) }
  }

  return (
    <>
      <section className="card" aria-labelledby="fam-goals-title">
        <h3 id="fam-goals-title" style={{ marginTop: 0 }}>Goals we set together</h3>
        <GoalList goals={data.goals} canDecide={false} />
        <GoalForm studentId={studentId} role="parent" onSaved={reload} />
      </section>

      {data.plan && (
        <section className="card" aria-labelledby="fam-plan-title">
          <h3 id="fam-plan-title" style={{ marginTop: 0 }}>{studentName}'s {data.plan.type === 'IEP' ? 'IEP' : '504 plan'}</h3>
          <PlanDoc plan={data.plan} />

          <form className="goal-form plan-suggest" onSubmit={suggest}>
            <label style={{ gridColumn: '1 / -1', fontWeight: 700 }}>
              Suggest an update to the plan
              <textarea rows={2} value={suggestion} maxLength={1000}
                placeholder="For example: Sam focuses better with the timer app we use at home - could that be added?"
                onChange={(e) => setSuggestion(e.target.value)} />
            </label>
            <button type="submit" className="btn-primary" disabled={busy || !suggestion.trim()}>
              Send to the teacher
            </button>
            <p className="muted" style={{ margin: 0, fontSize: '.82em', gridColumn: '1 / -1' }}>
              Plans are changed by the team, not by any one person - your suggestion goes to
              {' '}{data.plan.case_manager} to bring to the team, and you'll see the decision here.
            </p>
          </form>
          {data.plan_requests.length > 0 && (
            <ul className="plain-list" style={{ marginTop: 10 }}>
              {data.plan_requests.map((r) => (
                <li key={r.id} className="row between">
                  <span style={{ flex: 1 }}>{r.text}</span>
                  <span className={`chip ${r.status === 'accepted' ? 'mint' : r.status === 'proposed' ? 'cream' : ''}`}>
                    {r.status === 'proposed' ? 'with the teacher' : r.status}
                  </span>
                </li>
              ))}
            </ul>
          )}
        </section>
      )}
    </>
  )
}
