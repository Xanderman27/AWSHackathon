// The front page: Duolingo-simple. Capy snacks on grass at the left, one promise and two buttons on
// the right, and the login itself lives in a small dialog. Students use the login their
// teacher set; teachers and parents have their own.

import { useEffect, useRef, useState } from 'react'
import { useNavigate } from 'react-router-dom'
import { getSession, login, signUp } from '../api'
import Capy from '../components/Capy'
import JoinClass from '../components/JoinClass'
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
  const session = getSession()
  const dialogRef = useRef<HTMLDialogElement>(null)
  const userRef = useRef<HTMLInputElement>(null)
  const [username, setUsername] = useState('')
  const [password, setPassword] = useState('')
  const [busy, setBusy] = useState(false)
  const [err, setErr] = useState<string | null>(null)
  // 'signup' collects the family's details, 'child' is the step where they pick their learner.
  const [mode, setMode] = useState<'signup' | 'login' | 'child'>('signup')
  const [name, setName] = useState('')
  const [email, setEmail] = useState('')
  const [classCode, setClassCode] = useState('')

  useEffect(() => () => dialogRef.current?.close(), [])

  // Someone already signed in has no business on the login page: send them home. The header's
  // "Log out" and the hero's "Log in" can then never show at the same time.
  useEffect(() => {
    if (session && mode !== 'child') nav(`/${session.role}`, { replace: true })
  }, [session, nav, mode])

  function open(next: 'signup' | 'login') {
    setErr(null)
    setMode(next)
    const d = dialogRef.current
    if (d && !d.open) d.showModal()
    setTimeout(() => userRef.current?.focus(), 30)
  }

  async function submitSignUp(e: React.FormEvent) {
    e.preventDefault()
    if (busy) return
    setBusy(true); setErr(null)
    try {
      const result = await signUp({ name, email, password, classCode })
      // The account exists and they are signed in; now they choose which child is theirs.
      if (result.needs_child) setMode('child')
      else nav('/parent')
    } catch (ex) {
      setErr(ex instanceof Error ? ex.message : 'We could not create that account.')
    } finally {
      setBusy(false)
    }
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

  // A signed-in visitor gets bounced to their portal, so there is nothing to draw — except
  // during sign-up, where the session already exists but the family is still choosing their
  // child in the dialog on this page.
  if (session && mode !== 'child') return null

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
            <button type="button" className="btn-primary land-cta" onClick={() => open('signup')}>Get started</button>
            <button type="button" className="land-alt" onClick={() => open('login')}>I already have an account</button>
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

        {mode === 'child' ? (
          <div className="login-card" style={{ border: 0, padding: 0, boxShadow: 'none' }}>
            <JoinClass onJoined={() => { dialogRef.current?.close(); nav('/parent') }} />
          </div>
        ) : mode === 'signup' ? (
          <form className="login-card" style={{ border: 0, padding: 0, boxShadow: 'none' }} onSubmit={submitSignUp}>
            <h2 id="login-title" style={{ textAlign: 'center', marginBottom: 0 }}>Create your family account</h2>
            <p className="muted" style={{ margin: '0 0 4px', textAlign: 'center', fontSize: '.9em' }}>
              Ask your child's teacher for the class code.
            </p>
            {err && <p role="alert" className="feedback try" style={{ padding: '12px 16px', fontSize: '.95em' }}>{err}</p>}
            <label className="msg-field">
              <span>Your name</span>
              <input ref={userRef} type="text" value={name} autoComplete="name" required maxLength={80}
                onChange={(e) => setName(e.target.value)} placeholder="Alex Hulet" />
            </label>
            <label className="msg-field">
              <span>Email</span>
              <input type="email" value={email} autoComplete="email" required
                onChange={(e) => setEmail(e.target.value)} placeholder="you@example.com" />
            </label>
            <label className="msg-field">
              <span>Password</span>
              <input type="password" value={password} autoComplete="new-password" required minLength={8}
                onChange={(e) => setPassword(e.target.value)} placeholder="At least 8 characters" />
            </label>
            <label className="msg-field">
              <span>Class code</span>
              {/* Codes are spoken aloud and typed on a phone, so the server ignores case,
                  spaces and dashes; this input just makes it look like a code. */}
              <input type="text" value={classCode} required maxLength={20} className="code-input"
                autoCapitalize="characters" spellCheck={false}
                onChange={(e) => setClassCode(e.target.value)} placeholder="BRIGHT4" />
            </label>
            <button type="submit" className="btn-primary btn-lg"
              disabled={busy || !name || !email || password.length < 8 || !classCode}
              style={{ width: '100%', justifyContent: 'center' }}>
              {busy ? 'Creating your account…' : 'Create account'}
            </button>
            <p className="muted" style={{ margin: 0, fontSize: '.85em', textAlign: 'center' }}>
              Already have one?{' '}
              <button type="button" className="link-button" onClick={() => { setErr(null); setMode('login') }}>Log in instead</button>
            </p>
          </form>
        ) : (
          <form className="login-card" style={{ border: 0, padding: 0, boxShadow: 'none' }} onSubmit={submit}>
            <h2 id="login-title" style={{ textAlign: 'center', marginBottom: 4 }}>Log in</h2>
            {err && <p role="alert" className="feedback try" style={{ padding: '12px 16px', fontSize: '.95em' }}>{err}</p>}
            <label className="msg-field">
              <span>Username or email</span>
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
              Students: use the login your teacher gave you.{' '}
              <button type="button" className="link-button" onClick={() => { setErr(null); setMode('signup') }}>New family? Sign up</button>
            </p>
            <details className="demo-creds">
              <summary>Demo logins for judges</summary>
              <table>
                <tbody>
                  <tr><td>Student</td><td><code>sam</code></td><td><code>otter123</code></td></tr>
                  <tr><td>Student</td><td><code>mia</code></td><td><code>otter123</code></td></tr>
                  <tr><td>Teacher</td><td><code>rivera</code></td><td><code>teach123</code></td></tr>
                  <tr><td>Parent</td><td><code>jordan</code></td><td><code>family123</code></td></tr>
                  {/* Four seats at one table, so judges can open a team game against each other. */}
                  <tr><td>Judges</td><td><code>judge1</code>–<code>judge4</code></td><td><code>judge123</code></td></tr>
                </tbody>
              </table>
            </details>
          </form>
        )}
      </dialog>
    </div>
  )
}
