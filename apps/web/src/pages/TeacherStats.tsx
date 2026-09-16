// Classwide statistics: aggregate only, neutral language, no rankings.

import { useEffect, useState } from 'react'
import { api } from '../api'
import { BoltIcon, FlagIcon, StarIcon, TeamIcon } from '../components/PathArt'

interface SubjectStat { subject: string; learners: number; avg: number; below: number; proficient: number; above: number }
interface ClassStats { checkins: number; quests_done: number; stars: number; hints: number; active_learners: number; avg_estimate: number | null; subjects: SubjectStat[] }
interface Summary { students: { id: string }[]; class_stats: ClassStats }

const BUCKETS = [
  { key: 'below' as const, label: 'Below proficient', color: 'var(--zone-red)' },
  { key: 'proficient' as const, label: 'Proficient', color: 'var(--zone-green)' },
  { key: 'above' as const, label: 'Above proficient', color: 'var(--zone-blue)' },
]

export default function TeacherStats() {
  const [data, setData] = useState<Summary | null>(null)
  const [err, setErr] = useState<string | null>(null)
  useEffect(() => { api<Summary>('/teacher/class').then(setData).catch((e) => setErr(String(e))) }, [])

  if (err) return <p role="alert">{err}</p>
  if (!data) return <p>Loading…</p>
  const cs = data.class_stats

  return (
    <div className="stack">
      <div className="stat-grid">
        <div className="stat-card"><StarIcon size={34} /><div><div className="stat-num">{cs.stars}</div><div className="stat-lbl">Stars earned classwide</div></div></div>
        <div className="stat-card"><BoltIcon size={34} /><div><div className="stat-num">{cs.checkins}</div><div className="stat-lbl">Questions answered</div></div></div>
        <div className="stat-card"><FlagIcon size={34} /><div><div className="stat-num">{cs.quests_done}</div><div className="stat-lbl">Quests finished</div></div></div>
        <div className="stat-card"><TeamIcon size={34} /><div><div className="stat-num">{cs.active_learners}<span style={{ fontSize: '.55em', opacity: .7 }}>/{data.students.length}</span></div><div className="stat-lbl">Learners with evidence</div></div></div>
      </div>

      <section className="card">
        <div className="row between" style={{ marginBottom: 4 }}>
          <h2 style={{ margin: 0 }}>By subject</h2>
          <span className="row legend" style={{ marginTop: 0 }}>
            {BUCKETS.map((b) => <span key={b.key}><i style={{ background: b.color }} />{b.label}</span>)}
          </span>
        </div>
        <p className="muted" style={{ fontSize: '.88em' }}>
          Buckets follow the learner model's bands: below 40% is still building, 40–80% is practicing
          at grade level, above 80% is ready to stretch. Counts are learners with evidence in that subject.
        </p>
        <div className="subject-bars">
          {cs.subjects.map((s) => {
            const total = s.below + s.proficient + s.above
            return (
              <div className="sbar" key={s.subject}>
                <span className="sbar-name">{s.subject}</span>
                <span className="sbar-track stacked" role="img"
                  aria-label={`${s.subject}: ${s.below} below proficient, ${s.proficient} proficient, ${s.above} above proficient`}>
                  {BUCKETS.map((b) => s[b.key] > 0 && (
                    <i key={b.key} style={{ width: `${(s[b.key] / total) * 100}%`, background: b.color }}>
                      {s[b.key]}
                    </i>
                  ))}
                </span>
                <span className="sbar-val">{total} learner{total === 1 ? '' : 's'}</span>
              </div>
            )
          })}
        </div>
      </section>

      <div className="card" style={{ background: 'var(--surface-2)' }}>
        <strong>How this works.</strong> <span className="muted">These are class totals for your eyes only.
        Learners never see rankings or each other's numbers, and nothing here diagnoses, grades, or places a student.</span>
      </div>
    </div>
  )
}
