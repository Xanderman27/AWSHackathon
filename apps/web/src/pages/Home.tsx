// Sign-in page, kept as simple as Duolingo's: one card, two fields, one button.
// Students use the login their teacher set; teachers and parents have their own.

import { useState } from 'react'
import { useNavigate } from 'react-router-dom'
import { login } from '../api'
import Bear from '../components/Bear'

const FRAMEWORKS = [
  { abbr: 'IDEA', url: 'https://sites.ed.gov/idea/statuteregulations' },
  { abbr: 'Section 504', url: 'https://www.ed.gov/laws-and-policy/civil-rights-laws/disability-discrimination/protecting-students-with-disabilities' },
  { abbr: 'FERPA', url: 'https://studentprivacy.ed.gov/' },
  { abbr: 'COPPA', url: 'https://www.ftc.gov/business-guidance/privacy-security/childrens-privacy' },
  { abbr: 'WCAG 2.2 AA', url: 'https://www.w3.org/TR/WCAG22/' },
]

export default function Home() {
  const nav = useNavigate()
  const [username, setUsername] = useState('')
  const [password, setPassword] = useState('')
  const [busy, setBusy] = useState(false)
  const [err, setErr] = useState<string | null>(null)

  async function submit(e: React.FormEvent) {
    e.preventDefault()
    if (busy) return
    setBusy(true); setErr(null)
    try {
      const s = await login(username, password)
      nav(`/${s.role}`)
    } catch (ex) {
      setErr(String(ex).includes('bad-credentials')
        ? 'That username or password does not match. Try again.'
        : 'Something went wrong. Is the server running?')
      setBusy(false)
    }
  }

  return (
    <div className="page center student-theme">
      <div className="login-wrap">
        <div className="login-hello reveal">
          <Bear size={110} mood="wave" float />
          <h1 className="login-brand">Dori</h1>
          <p className="muted" style={{ margin: 0, textAlign: 'center' }}>
            Learning that listens, for students with IEPs and 504 plans.
          </p>
        </div>

        <form className="card login-card reveal" style={{ animationDelay: '120ms' }} onSubmit={submit}>
          <h2 style={{ textAlign: 'center' }}>Log in</h2>
          {err && <p role="alert" className="feedback try" style={{ padding: '12px 16px', fontSize: '.95em' }}>{err}</p>}
          <label className="msg-field">
            <span>Username</span>
            <input type="text" value={username} autoComplete="username" required
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

        <ul className="login-frameworks reveal" style={{ animationDelay: '220ms' }} aria-label="Built to follow">
          {FRAMEWORKS.map((f) => (
            <li key={f.abbr}><a href={f.url} target="_blank" rel="noreferrer noopener">{f.abbr}</a></li>
          ))}
        </ul>
      </div>
    </div>
  )
}
