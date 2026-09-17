// What the teacher sent home about this family's own child, newest first.
//
// This is the receiving end of the teacher's "Send an update home" tab. It is deliberately a
// feed and not a chat: the two-way conversation already exists in the messages panel, and a
// family should be able to read what the teacher said without owing a reply.

import { useEffect, useState } from 'react'
import { api } from '../api'
import { updateDate } from '../components/FamilyUpdateComposer'

interface ParentUpdate {
  id: string
  student_id: string
  student_name: string
  teacher_name: string
  headline: string
  note: string
  happened_on: string
  created_at: string
  unread: boolean
}

export default function ParentUpdates() {
  const [updates, setUpdates] = useState<ParentUpdate[] | null>(null)
  const [error, setError] = useState('')

  useEffect(() => {
    api<{ updates: ParentUpdate[] }>('/parent/family-updates')
      .then((data) => setUpdates(data.updates))
      .catch(() => setError('Your updates could not load.'))
  }, [])

  // Opening the page is the read receipt. Nothing here is marked read on the teacher's side
  // until a guardian has actually had the chance to see it.
  useEffect(() => {
    const unread = (updates ?? []).filter((row) => row.unread)
    if (unread.length === 0) return
    Promise.all(unread.map((row) => api(`/parent/family-updates/${row.id}/read`, { method: 'POST' })))
      .catch(() => { /* the note is already on screen; a failed receipt is not worth an alert */ })
  }, [updates])

  if (error) return <p role="alert">{error}</p>
  if (updates === null) return <p>Loading your updates…</p>

  return (
    <div className="stack">
      <section className="card" aria-labelledby="updates-intro">
        <h2 id="updates-intro" style={{ marginTop: 0 }}>Updates from school</h2>
        <p className="muted" style={{ margin: 0 }}>
          Short notes your child's teacher sent about their day. Only your family can see these.
          To reply, use the messages button in the corner.
        </p>
      </section>

      {updates.length === 0 ? (
        <div className="card"><p className="muted" style={{ margin: 0 }}>
          No updates yet. When a teacher sends one about your child, it will appear here.
        </p></div>
      ) : (
        <ol className="update-list">
          {updates.map((row) => (
            <li key={row.id}>
              <article className={`card update-card ${row.unread ? 'is-new' : ''}`}>
                <div className="update-head">
                  <div>
                    <h3>{row.headline}</h3>
                    <p className="muted update-meta">
                      {row.teacher_name} · about {row.student_name} · {updateDate(row.happened_on)}
                    </p>
                  </div>
                  {row.unread && <span className="update-new-flag">New</span>}
                </div>
                <p className="update-note">{row.note}</p>
              </article>
            </li>
          ))}
        </ol>
      )}
    </div>
  )
}
