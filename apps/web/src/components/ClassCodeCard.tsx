// The code a teacher reads out so families can find this classroom. It is the only thing
// between a stranger and the sign-up form, so the teacher can replace it whenever they like.

import { useEffect, useState } from 'react'
import { api } from '../api'

interface ClassCode {
  class_id: string
  class_name: string
  code: string
  families_joined: number
  families_choosing: number
}

export default function ClassCodeCard() {
  const [info, setInfo] = useState<ClassCode | null>(null)
  const [copied, setCopied] = useState(false)
  const [busy, setBusy] = useState(false)
  const [confirming, setConfirming] = useState(false)
  const [err, setErr] = useState('')

  useEffect(() => {
    api<ClassCode>('/teacher/class-code').then(setInfo).catch(() => setErr('The class code could not load.'))
  }, [])

  async function copy() {
    if (!info) return
    try {
      await navigator.clipboard.writeText(info.code)
      setCopied(true)
      setTimeout(() => setCopied(false), 2400)
    } catch {
      setErr('Copying is blocked in this browser. The code is written above.')
    }
  }

  async function rotate() {
    setBusy(true); setErr('')
    try {
      setInfo(await api<ClassCode>('/teacher/class-code/rotate', { method: 'POST' }))
      setConfirming(false)
    } catch {
      setErr('A new code could not be made.')
    } finally {
      setBusy(false)
    }
  }

  if (err && !info) return <div className="card feedback try" role="alert">{err}</div>
  if (!info) return <div className="card"><p style={{ margin: 0 }}>Loading your class code…</p></div>

  return (
    <section className="card class-code-card" aria-labelledby="class-code-title">
      <div>
        <span className="chip cream">Families</span>
        <h2 id="class-code-title">Your class code</h2>
        <p className="muted">
          Families type this on the front page to create an account and join {info.class_name}. They
          then choose their own child, and only ever see that child.
        </p>
      </div>

      <div className="code-block">
        <output className="code-value" aria-label={`Class code: ${info.code.split('').join(' ')}`}>{info.code}</output>
        <div className="row">
          <button type="button" className="btn-primary" onClick={copy}>
            {copied ? '✓ Copied' : 'Copy code'}
          </button>
          {confirming ? (
            <span className="row rotate-confirm">
              <span className="muted">Old code stops working. Sure?</span>
              <button type="button" disabled={busy} onClick={rotate}>{busy ? 'Making…' : 'Yes, make a new one'}</button>
              <button type="button" onClick={() => setConfirming(false)}>Keep this one</button>
            </span>
          ) : (
            <button type="button" onClick={() => setConfirming(true)}>Make a new code</button>
          )}
        </div>
      </div>

      <p className="muted class-code-counts">
        <strong>{info.families_joined}</strong> famil{info.families_joined === 1 ? 'y has' : 'ies have'} joined
        {info.families_choosing > 0 && <> · <strong>{info.families_choosing}</strong> still choosing their child</>}
      </p>
      {err && <div className="feedback try" role="alert">{err}</div>}
    </section>
  )
}
