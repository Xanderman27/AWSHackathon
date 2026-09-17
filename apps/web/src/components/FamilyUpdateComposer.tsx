// A note home about one learner. The class blog spoke to every family at once; this speaks to
// one, because the thing worth saying about a day is usually about one child.
//
// The note carries no category. A good day and a hard day are written and read in the same
// shape: a label on the envelope tells a family how to feel before they have read a word, and
// the language guide in docs/GUIDELINES.md §9 rules out the deficit vocabulary such a label
// would introduce. What happened goes in the teacher's own words.
//
// The audience line is always visible. A teacher should never have to guess who is about to
// read what they typed.

import { useEffect, useMemo, useState } from 'react'
import { api } from '../api'
import Avatar, { type AvatarSpec } from './Avatar'

interface Learner { id: string; display_name: string; photo?: string | null; avatar?: AvatarSpec | null }
interface ClassSummary { students: Learner[] }
interface Recipient { student_id: string; student_name: string; guardians: string[] }

/** "Jordan Bell", or "Jordan Bell and Sam Bell" for two guardians. */
function nameList(names: string[]) {
  if (names.length === 0) return ''
  if (names.length === 1) return names[0]
  return `${names.slice(0, -1).join(', ')} and ${names[names.length - 1]}`
}

export interface FamilyUpdate {
  id: string
  student_id: string
  student_name: string
  headline: string
  note: string
  happened_on: string
  created_at: string
  sent_to: string[]
  seen: boolean
}

export function updateDate(raw: string) {
  const parts = /^(\d{4})-(\d{2})-(\d{2})$/.exec(raw)
  const when = parts ? new Date(Number(parts[1]), Number(parts[2]) - 1, Number(parts[3])) : new Date(raw)
  return Number.isNaN(when.getTime())
    ? '' : when.toLocaleDateString(undefined, { weekday: 'long', month: 'long', day: 'numeric' })
}

export default function FamilyUpdateComposer() {
  const [learners, setLearners] = useState<Learner[]>([])
  const [recipients, setRecipients] = useState<Recipient[]>([])
  const [sent, setSent] = useState<FamilyUpdate[] | null>(null)
  const [studentId, setStudentId] = useState('')
  const [headline, setHeadline] = useState('')
  const [note, setNote] = useState('')
  const [happenedOn, setHappenedOn] = useState(() => new Date().toISOString().slice(0, 10))
  const [busy, setBusy] = useState(false)
  const [notice, setNotice] = useState('')
  const [error, setError] = useState('')

  useEffect(() => {
    api<ClassSummary>('/teacher/class')
      .then((data) => setLearners(data.students))
      .catch(() => setError('Your class list could not load.'))
    api<Recipient[]>('/teacher/family-updates/recipients')
      .then(setRecipients)
      .catch(() => setError('The guardian list could not load.'))
    api<FamilyUpdate[]>('/teacher/family-updates')
      .then(setSent)
      .catch(() => setError('Your sent updates could not load.'))
  }, [])

  const chosen = useMemo(() => learners.find((l) => l.id === studentId) ?? null, [learners, studentId])
  const chosenGuardians = useMemo(
    () => recipients.find((r) => r.student_id === studentId)?.guardians ?? [],
    [recipients, studentId],
  )
  const ready = Boolean(studentId && headline.trim() && note.trim()) && !busy

  async function send() {
    if (!ready) return
    setBusy(true); setError(''); setNotice('')
    try {
      const saved = await api<FamilyUpdate>('/teacher/family-updates', {
        method: 'POST',
        body: JSON.stringify({ student_id: studentId, headline, note, happened_on: happenedOn }),
      })
      setSent((current) => [saved, ...(current ?? [])])
      setHeadline(''); setNote('')
      setNotice(`Sent to ${saved.sent_to.join(' and ') || `${saved.student_name}'s family`}. No other family can see it.`)
    } catch (problem) {
      setError(String(problem).includes('409')
        ? 'No family is linked to that learner yet, so there is nobody to send this to.'
        : 'That update could not be sent. Please try again.')
    } finally {
      setBusy(false)
    }
  }

  async function remove(id: string) {
    setError(''); setNotice('')
    try {
      await api(`/teacher/family-updates/${id}`, { method: 'DELETE' })
      setSent((current) => (current ?? []).filter((row) => row.id !== id))
      setNotice('Removed. That family no longer sees it.')
    } catch {
      setError('That update could not be removed.')
    }
  }

  return (
    <div className="stack">
      <section className="card blog-composer" aria-labelledby="update-title">
        <div>
          <span className="chip sky">One family</span>
          <h2 id="update-title">Send an update home</h2>
          <p className="muted">
            Something that went well, or something a family should hear from you before they hear
            it from their child. It goes to that learner's guardians and nobody else.
          </p>
        </div>

        <div className="composer-fields">
          <label className="msg-field">
            <span>Which learner?</span>
            <select value={studentId} onChange={(event) => setStudentId(event.target.value)}>
              <option value="">Choose a learner…</option>
              {learners.map((learner) => {
                const guardians = recipients.find((r) => r.student_id === learner.id)?.guardians ?? []
                return (
                  <option key={learner.id} value={learner.id}>
                    {learner.display_name}
                    {guardians.length ? ` — to ${nameList(guardians)}` : ' — no family linked yet'}
                  </option>
                )
              })}
            </select>
          </label>

          <label className="msg-field">
            <span>Headline</span>
            <input value={headline} maxLength={80} placeholder="She explained her thinking to the whole table"
              onChange={(event) => setHeadline(event.target.value)} />
          </label>

          <label className="msg-field">
            <span>What happened?</span>
            <textarea value={note} maxLength={600} rows={4}
              placeholder="What happened, and what you would like this family to know. One or two sentences they can bring up at home."
              onChange={(event) => setNote(event.target.value)} />
          </label>

          <div className="composer-actions">
            <label className="msg-field composer-date">
              <span>Day</span>
              <input type="date" value={happenedOn} onChange={(event) => setHappenedOn(event.target.value)} />
            </label>
            <div className="row">
              {(headline || note) && (
                <button type="button" onClick={() => { setHeadline(''); setNote('') }} disabled={busy}>Discard</button>
              )}
              <button type="button" className="btn-primary btn-lg" disabled={!ready} onClick={send}>
                {busy ? 'Sending…' : 'Send to this family'}
              </button>
            </div>
          </div>
        </div>

        <p className="muted photo-audience">
          <strong>Who sees this:</strong>{' '}
          {chosen && chosenGuardians.length > 0
            ? <>{nameList(chosenGuardians)}, {chosen.display_name}'s
                {chosenGuardians.length === 1 ? ' guardian' : ' guardians'}. No other family, and
                not {chosen.display_name}.</>
            : chosen
              ? <>nobody yet — no family is linked to {chosen.display_name}.</>
              : <>only the guardians linked to the learner you choose. Students never see these.</>}
        </p>

        {notice && <div className="feedback good" role="status">✓ {notice}</div>}
        {error && <div className="feedback try" role="alert">{error}</div>}
      </section>

      <section aria-labelledby="sent-title">
        <div className="row between" style={{ marginBottom: 12 }}>
          <h2 id="sent-title" style={{ margin: 0 }}>Sent so far</h2>
          {sent && <span className="muted">{sent.length} update{sent.length === 1 ? '' : 's'}</span>}
        </div>

        {sent === null ? <p className="muted">Loading your updates…</p> : sent.length === 0 ? (
          <div className="card"><p className="muted" style={{ margin: 0 }}>
            Nothing sent yet. One sentence about a good moment goes a long way.
          </p></div>
        ) : (
          <ol className="update-list">
            {sent.map((row) => {
              const learner = learners.find((l) => l.id === row.student_id)
              return (
                <li key={row.id}>
                  <article className="card update-card">
                    <div className="update-head">
                      <Avatar photo={learner?.photo} spec={learner?.avatar} size={40} />
                      <div>
                        <h3>{row.headline}</h3>
                        <p className="muted update-meta">
                          About {row.student_name} · {updateDate(row.happened_on)}
                        </p>
                      </div>
                    </div>
                    <p className="update-note">{row.note}</p>
                    <div className="row between update-foot">
                      <span className="muted">
                        Sent to {row.sent_to.join(' and ') || 'no linked family'}
                        {row.seen ? ' · opened' : ' · not opened yet'}
                      </span>
                      <button type="button" className="table-btn" onClick={() => remove(row.id)}>Remove</button>
                    </div>
                  </article>
                </li>
              )
            })}
          </ol>
        )}
      </section>
    </div>
  )
}
