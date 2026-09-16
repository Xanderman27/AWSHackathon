import { useNavigate } from 'react-router-dom'
import { setSession, type Role } from '../api'
import Bear from '../components/Bear'

const ROLES: { role: Role; userId: string; label: string; blurb: string; emoji: string; tone: string }[] = [
  { role: 'student', userId: 'student-01', label: 'I am a student', blurb: 'Play a quest or a game.', emoji: '🧒', tone: 'mint' },
  { role: 'teacher', userId: 'teacher-01', label: 'I am a teacher', blurb: 'See the class and each learner.', emoji: '🧑‍🏫', tone: 'sky' },
  { role: 'parent', userId: 'parent-01', label: 'I am a parent', blurb: "See your child's progress and your rights.", emoji: '👪', tone: 'cream' },
]

// Typographic badges, not agency seals: reproducing a government seal would imply endorsement.
const FRAMEWORKS = [
  { abbr: 'IDEA', full: 'Individuals with Disabilities Education Act', url: 'https://sites.ed.gov/idea/statuteregulations', glyph: '🏛' },
  { abbr: 'Section 504', full: 'Rehabilitation Act of 1973', url: 'https://www.ed.gov/laws-and-policy/civil-rights-laws/disability-discrimination/protecting-students-with-disabilities', glyph: '⚖️' },
  { abbr: 'FERPA', full: 'Family Educational Rights and Privacy Act', url: 'https://studentprivacy.ed.gov/', glyph: '🔒' },
  { abbr: 'COPPA', full: "Children's Online Privacy Protection Rule", url: 'https://www.ftc.gov/business-guidance/privacy-security/childrens-privacy', glyph: '🛡' },
  { abbr: 'WCAG 2.2 AA', full: 'Web Content Accessibility Guidelines', url: 'https://www.w3.org/TR/WCAG22/', glyph: '♿' },
]

export default function Home() {
  const nav = useNavigate()
  return (
    <div className="page">
      <section className="hero">
        <div>
          <span className="eyebrow reveal" style={{ animationDelay: '40ms' }}>
            <span aria-hidden="true">✨</span> Built for students with IEPs and 504 plans
          </span>
          <h1 className="reveal" style={{ animationDelay: '120ms' }}>
            Learning that <span className="underline">listens</span> to every kid.
          </h1>
          <p className="lede reveal muted" style={{ animationDelay: '200ms' }}>
            Dori turns short, friendly check-ins into clear next steps for teachers and
            plain-language progress for families, so nobody waits until the next meeting to
            find out how a child is doing.
          </p>
          <div className="role-list" role="group" aria-label="Choose who you are">
            {ROLES.map((r, i) => (
              <button key={r.role} type="button" className="role reveal"
                style={{ animationDelay: `${280 + i * 90}ms` }}
                onClick={() => { setSession({ role: r.role, userId: r.userId }); nav(`/${r.role}`) }}>
                <span className={`ico ${r.tone}`} aria-hidden="true">{r.emoji}</span>
                <span><strong>{r.label}</strong><span className="sub">{r.blurb}</span></span>
                <span className="go" aria-hidden="true">→</span>
              </button>
            ))}
          </div>
        </div>

        <div className="hero-art" aria-hidden="true">
          <div className="tile tall pop" style={{ background: 'var(--brand)', animationDelay: '160ms' }}>
            <Bear size={132} mood="wave" float />
          </div>
          <div className="tile pop" style={{ background: 'var(--mint)', animationDelay: '300ms' }}>
            <span className="tile-glyph floaty" style={{ animationDelay: '.4s' }}>🔢</span>
          </div>
          <div className="tile pop" style={{ background: 'var(--cream)', animationDelay: '420ms' }}>
            <span className="tile-glyph floaty" style={{ animationDelay: '.9s' }}>📖</span>
          </div>
        </div>
      </section>

      <section className="compliance reveal" style={{ animationDelay: '620ms' }} aria-labelledby="frameworks-title">
        <h2 id="frameworks-title" className="compliance-title">Built to follow</h2>
        <ul className="badge-row">
          {FRAMEWORKS.map((f) => (
            <li key={f.abbr}>
              <a className="badge" href={f.url} target="_blank" rel="noreferrer noopener" title={f.full}>
                <span className="badge-glyph" aria-hidden="true">{f.glyph}</span>
                <span className="badge-text">
                  <strong>{f.abbr}</strong>
                  <span>{f.full}</span>
                </span>
              </a>
            </li>
          ))}
        </ul>
      </section>
    </div>
  )
}
