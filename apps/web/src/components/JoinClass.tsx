// The second half of signing up: a class code says which classroom, never which child, so
// the family picks theirs here. The list only ever contains learners from the class the code
// opened, and it is gone the moment they choose.

import { useEffect, useState } from 'react'
import { api } from '../api'
import Avatar, { type AvatarSpec } from './Avatar'

interface Candidate { id: string; display_name: string; photo?: string | null; avatar?: AvatarSpec | null }
interface JoinState { needs_child: boolean; class_name: string | null; candidates: Candidate[] }

export default function JoinClass({ onJoined }: { onJoined: () => void }) {
  const [state, setState] = useState<JoinState | null>(null)
  const [picked, setPicked] = useState<string | null>(null)
  const [busy, setBusy] = useState(false)
  const [err, setErr] = useState('')

  useEffect(() => {
    api<JoinState>('/parent/join').then(setState).catch(() => setErr('We could not load your class. Please try again.'))
  }, [])

  async function claim() {
    if (!picked || busy) return
    setBusy(true); setErr('')
    try {
      await api('/parent/join', { method: 'POST', body: JSON.stringify({ student_id: picked }) })
      onJoined()
    } catch {
      setErr('That child could not be linked to your account. Please check with the teacher.')
    } finally {
      setBusy(false)
    }
  }

  if (!state) return <p className="muted">Finding your class…</p>

  return (
    <div className="join-step">
      <h2 style={{ margin: 0 }}>Which child is yours?</h2>
      <p className="muted" style={{ margin: 0 }}>
        You joined <strong>{state.class_name}</strong>. Choose your child so we show you their
        progress and nobody else's.
      </p>
      {err && <p role="alert" className="feedback try" style={{ padding: '12px 16px', fontSize: '.95em' }}>{err}</p>}

      <ul className="join-grid" role="group" aria-label="Choose your child">
        {state.candidates.map((child) => (
          <li key={child.id}>
            <button type="button" className={`join-child ${picked === child.id ? 'picked' : ''}`}
              aria-pressed={picked === child.id} onClick={() => setPicked(child.id)}>
              <Avatar photo={child.photo} spec={child.avatar} size={64} />
              <strong>{child.display_name}</strong>
            </button>
          </li>
        ))}
      </ul>

      <button type="button" className="btn-primary btn-lg" style={{ width: '100%', justifyContent: 'center' }}
        disabled={!picked || busy} onClick={claim}>
        {busy ? 'Linking…' : 'This is my child'}
      </button>
      <p className="muted" style={{ margin: 0, fontSize: '.85em', textAlign: 'center' }}>
        Your teacher can see which families have joined and can fix a wrong choice.
      </p>
    </div>
  )
}
