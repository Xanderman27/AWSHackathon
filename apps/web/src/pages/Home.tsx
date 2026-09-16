// The front page: Duolingo-simple. Capy snacks on grass at the left, one promise and two buttons on
// the right, and the login itself lives in a small dialog. Students use the login their
// teacher set; teachers and parents have their own.

import { useEffect, useRef, useState } from 'react'
import { useNavigate } from 'react-router-dom'
import { login } from '../api'
import Capy from '../components/Capy'
import { BookIcon, FlagIcon, StarIcon } from '../components/PathArt'

const FRAMEWORKS = [
  { abbr: 'IDEA', url: 'https://sites.ed.gov/idea/statuteregulations' },
  { abbr: 'Section 504', url: 'https://www.ed.gov/laws-and-policy/civil-rights-laws/disability-discrimination/protecting-students-with-disabilities' },
  { abbr: 'FERPA', url: 'https://studentprivacy.ed.gov/' },
  { abbr: 'COPPA', url: 'https://www.ftc.gov/business-guidance/privacy-security/childrens-privacy' },
  { abbr: 'WCAG 2.2 AA', url: 'https://www.w3.org/TR/WCAG22/' },
]

const SUBJECTS = [
  { name: 'English', color: '#1cb0f6' },
  { name: 'Science', color: '#ce82ff' },
  { name: 'Math', color: '#ffb020' },
  { name: 'History', color: '#57cf78' },
  { name: 'Geography', color: '#f27d98' },
]

export default function Home() {
  const nav = useNavigate()
  const dialogRef = useRef<HTMLDialogElement>(null)
  const userRef = useRef<HTMLInputElement>(null)
  const [username, setUsername] = useState('')
  const [password, setPassword] = useState('')
  const [busy, setBusy] = useState(false)
  const [err, setErr] = useState<string | null>(null)

  useEffect(() => () => dialogRef.current?.close(), [])

  function openLogin() {
    setErr(null)
    const d = dialogRef.current
    if (d && !d.open) d.showModal()
    setTimeout(() => userRef.current?.focus(), 30)
  }

  async function submit(e: React.FormEvent) {
    e.preventDefault()
    if (busy) return
    setBusy(true); setErr(null)
    try {
      const s = await login(username, password)
      dialogRef.current?.close()
      nav(`/${s.role}`)
    } catch (ex) {
      setErr(String(ex).includes('bad-credentials')
        ? 'That username or password does not match. Try again.'
        : 'Something went wrong. Is the server running?')
      setBusy(false)
    }
  }

  return (
    <div className="page land">
      <section className="land-hero">
        <div className="land-stage">
          <div className="land-blob" aria-hidden="true"></div>
          <div className="land-capy">
            <Capy size={380} mood="happy" float />
            <span className="land-drift da" aria-hidden="true"><StarIcon size={54} /></span>
            <span className="land-drift db" aria-hidden="true"><BookIcon size={58} /></span>
            <span className="land-drift dc" aria-hidden="true"><FlagIcon size={50} /></span>
          </div>
        </div>

        <div className="land-right">
          <span className="eyebrow" style={{ marginBottom: 0 }}>For students with IEPs &amp; 504 plans</span>
          <h1 className="land-h1">Learning that <span className="underline">listens</span> to every kid.</h1>
          <p className="lede muted" style={{ margin: 0 }}>
            Inclusive by design: students of every ability learn, play, and collaborate together.
            Parents and teachers stay in the loop, so the right support reaches each child at the
            right moment.
          </p>
          <div className="land-ctas">
            <button type="button" className="btn-primary land-cta" onClick={openLogin}>Get started</button>
            <button type="button" className="land-alt" onClick={openLogin}>I already have an account</button>
          </div>
        </div>
      </section>

      <div className="land-pills" aria-label="Subjects">
        {SUBJECTS.map((s) => (
          <span className="land-pill" key={s.name}>
            <span className="pill-dot" style={{ background: s.color }} aria-hidden="true"></span>{s.name}
          </span>
        ))}
      </div>

      <p className="land-foot">
        Built to follow{' '}
        {FRAMEWORKS.map((f, i) => (
          <span key={f.abbr}>{i > 0 && ' · '}<a href={f.url} target="_blank" rel="noreferrer noopener">{f.abbr}</a></span>
        ))}
      </p>

      <dialog ref={dialogRef} className="login-dialog" aria-labelledby="login-title"
        onClick={(e) => { if (e.target === dialogRef.current) dialogRef.current?.close() }}>
        <form className="login-card" style={{ border: 0, padding: 0, boxShadow: 'none' }} onSubmit={submit}>
          <h2 id="login-title" style={{ textAlign: 'center', marginBottom: 4 }}>Log in</h2>
          {err && <p role="alert" className="feedback try" style={{ padding: '12px 16px', fontSize: '.95em' }}>{err}</p>}
          <label className="msg-field">
            <span>Username</span>
            <input ref={userRef} type="text" value={username} autoComplete="username" required
              onChange={(e) => setUsername(e.target.value)} placeholder="Your username" />
          </label>
          <label className="msg-field">
            <span>Password</span>
            <input type="password" value={password} autoComplete="current-password" required
              onChange={(e) => setPassword(e.target.value)} placeholder="Your password" />
          </label>
          <button type="submit" className="btn-primary btn-lg" disabled={busy || !username || !password}
            style={{ width: '100%', justifyContent: 'center' }}>
            {busy ? 'Logging in…' : 'Log in'}
          </button>
          <p className="muted" style={{ margin: 0, fontSize: '.85em', textAlign: 'center' }}>
            Students: use the login your teacher gave you.
          </p>
          <details className="demo-creds">
            <summary>Demo logins for judges</summary>
            <table>
              <tbody>
                <tr><td>Student</td><td><code>sam</code></td><td><code>otter123</code></td></tr>
                <tr><td>Teacher</td><td><code>rivera</code></td><td><code>teach123</code></td></tr>
                <tr><td>Parent</td><td><code>jordan</code></td><td><code>family123</code></td></tr>
              </tbody>
            </table>
          </details>
        </form>
      </dialog>
    </div>
  )
}
