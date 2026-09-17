// Classwide statistics: aggregate only, neutral language, no rankings.
//
// What this page is allowed to be, from docs/GUIDELINES.md §7:
//
// - Evidence, then interpretation, in that order. Every panel says what it counted and over
//   what window, because a number a teacher cannot source is a number they cannot defend
//   (§1.3, the Endrew F. "cogent and responsive explanation" requirement in interface form).
// - Confidence travels with the estimate. A class average with no confidence mix invites a
//   decision the evidence cannot support, so the mix is its own panel and "needs more
//   evidence" is reported as a normal state rather than a failure (§5.4).
// - Neutral words only. No "struggling", "weak", "behind", "at risk" (§9).
// - Collaboration drift is surfaced (§5.9): a grouping feature can pass every composition
//   rule on any single run and still produce tracking across a term.
//
// And what it must not be: no learner is named, ranked or ordered here. An individual's
// evidence lives on their own page, which is where a teacher can act on it.

import { useEffect, useState } from 'react'
import { api } from '../api'
import { BoltIcon, BulbIcon, FlagIcon, StarIcon, TeamIcon, TreasureMapIcon } from '../components/PathArt'

interface SubjectStat { subject: string; learners: number; avg: number; below: number; proficient: number; above: number }
interface DayStat { date: string; answers: number; quests: number }
interface Collaboration {
  activities: number; learners_grouped: number; never_grouped: number
  diversity: number; repeat_pairs: number
}
interface ClassStats {
  checkins: number; quests_done: number; stars: number; hints: number
  active_learners: number; avg_estimate: number | null; subjects: SubjectStat[]
  answered_window: number; accuracy: number | null; hint_rate: number | null
  confidence_mix: { low: number; medium: number; high: number }
  needs_more_evidence: number; active_this_week: number
  daily: DayStat[]; collaboration: Collaboration
}
interface Summary { students: { id: string }[]; class_stats: ClassStats }

const BUCKETS = [
  { key: 'below' as const, label: 'Below proficient', color: 'var(--zone-red)' },
  { key: 'proficient' as const, label: 'Proficient', color: 'var(--zone-green)' },
  { key: 'above' as const, label: 'Above proficient', color: 'var(--zone-blue)' },
]

// Confidence is ordered low to high and labelled, never colour alone (WCAG SC 1.4.1).
const CONFIDENCE = [
  { key: 'high' as const, label: 'High confidence', color: 'var(--zone-green)' },
  { key: 'medium' as const, label: 'Medium', color: 'var(--zone-yellow)' },
  { key: 'low' as const, label: 'Needs more evidence', color: 'var(--zone-red)' },
]

const pct = (n: number | null) => (n === null ? '—' : `${Math.round(n * 100)}%`)

function dayLabel(iso: string) {
  const [y, m, d] = iso.split('-').map(Number)
  return new Date(y, m - 1, d).toLocaleDateString(undefined, { weekday: 'short', day: 'numeric' })
}

export default function TeacherStats() {
  const [data, setData] = useState<Summary | null>(null)
  const [err, setErr] = useState<string | null>(null)
  useEffect(() => { api<Summary>('/teacher/class').then(setData).catch((e) => setErr(String(e))) }, [])

  if (err) return <p role="alert">{err}</p>
  if (!data) return <p>Loading…</p>
  const cs = data.class_stats
  const learners = data.students.length
  const rows = cs.confidence_mix.low + cs.confidence_mix.medium + cs.confidence_mix.high
  const peak = Math.max(1, ...cs.daily.map((d) => d.answers))
  const collab = cs.collaboration

  return (
    <div className="stack">
      <div className="stat-grid">
        <div className="stat-card"><StarIcon size={34} /><div><div className="stat-num">{cs.stars}</div><div className="stat-lbl">Stars earned classwide</div></div></div>
        <div className="stat-card"><BoltIcon size={34} /><div><div className="stat-num">{cs.checkins}</div><div className="stat-lbl">Questions answered</div></div></div>
        <div className="stat-card"><FlagIcon size={34} /><div><div className="stat-num">{cs.quests_done}</div><div className="stat-lbl">Quests finished</div></div></div>
        <div className="stat-card"><TeamIcon size={34} /><div><div className="stat-num">{cs.active_learners}<span className="stat-of">/{learners}</span></div><div className="stat-lbl">Learners with evidence</div></div></div>
        <div className="stat-card"><TreasureMapIcon size={34} /><div><div className="stat-num">{pct(cs.accuracy)}</div><div className="stat-lbl">Answered correctly</div></div></div>
        <div className="stat-card"><BulbIcon size={34} /><div><div className="stat-num">{cs.hints}<span className="stat-of">{pct(cs.hint_rate)}</span></div><div className="stat-lbl">Hints opened</div></div></div>
      </div>

      <section className="card" aria-labelledby="activity-title">
        <div className="row between" style={{ marginBottom: 2 }}>
          <h2 id="activity-title" style={{ margin: 0 }}>Answers over the last {cs.daily.length} days</h2>
          <span className="muted" style={{ fontSize: '.85em', fontWeight: 600 }}>
            {cs.active_this_week} of {learners} answered something this week
          </span>
        </div>
        <p className="muted" style={{ fontSize: '.88em' }}>
          One column per day. Quiet days are normal; a run of them is worth a look, because
          evidence older than a fortnight is not evidence of where a learner is now.
        </p>

        <div className="actchart" role="img"
          aria-label={`Daily answers for the last ${cs.daily.length} days. The table below has the same numbers.`}>
          {cs.daily.map((day) => (
            <div className="actday" key={day.date}>
              <span className="actbar-wrap">
                {day.answers > 0 && (
                  <span className="actbar" style={{ height: `${(day.answers / peak) * 100}%` }}>
                    <span className="actval">{day.answers}</span>
                  </span>
                )}
              </span>
              <span className="actlbl">{dayLabel(day.date)}</span>
            </div>
          ))}
        </div>

        {/* A table, not a tooltip: hover is not an accessible way to reach a number. */}
        <details className="act-table">
          <summary>See the numbers as a table</summary>
          <table>
            <caption className="visually-hidden">Answers and quests finished per day</caption>
            <thead><tr><th scope="col">Day</th><th scope="col">Answers</th><th scope="col">Quests finished</th></tr></thead>
            <tbody>
              {cs.daily.map((day) => (
                <tr key={day.date}>
                  <th scope="row">{dayLabel(day.date)}</th>
                  <td>{day.answers}</td>
                  <td>{day.quests}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </details>
      </section>

      <section className="card" aria-labelledby="subject-title">
        <div className="row between" style={{ marginBottom: 4 }}>
          <h2 id="subject-title" style={{ margin: 0 }}>By subject</h2>
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

      <section className="card" aria-labelledby="evidence-title">
        <h2 id="evidence-title" style={{ margin: 0 }}>How much evidence is behind these numbers</h2>
        <p className="muted" style={{ fontSize: '.88em' }}>
          Confidence comes from how many relevant answers a learner has given on a skill and how
          steady they were. It is not a judgement about the learner. Low confidence is the model
          saying it does not know yet, which is the honest answer and the one worth acting on.
        </p>
        <div className="conf-bar" role="img"
          aria-label={`Across ${rows} learner-and-skill pairs: ${cs.confidence_mix.high} high confidence, ${cs.confidence_mix.medium} medium, ${cs.confidence_mix.low} needing more evidence.`}>
          {CONFIDENCE.map((c) => cs.confidence_mix[c.key] > 0 && (
            <i key={c.key} style={{ width: `${(cs.confidence_mix[c.key] / rows) * 100}%`, background: c.color }}>
              {cs.confidence_mix[c.key]}
            </i>
          ))}
        </div>
        <span className="row legend">
          {CONFIDENCE.map((c) => <span key={c.key}><i style={{ background: c.color }} />{c.label}</span>)}
        </span>
        {cs.needs_more_evidence > 0 && (
          <p className="stat-note">
            <strong>{cs.needs_more_evidence}</strong> learner-and-skill pair{cs.needs_more_evidence === 1 ? '' : 's'} need
            {cs.needs_more_evidence === 1 ? 's' : ''} more evidence before the model will
            recommend anything. A short quest is usually enough. The Learners tab shows which.
          </p>
        )}
      </section>

      <section className="card" aria-labelledby="collab-title">
        <h2 id="collab-title" style={{ margin: 0 }}>Group work</h2>
        <p className="muted" style={{ fontSize: '.88em' }}>
          Any composition rule applied over and over becomes a track, so these watch the pattern
          rather than a single activity. Names are deliberately absent: this is the class view.
        </p>
        <div className="collab-grid">
          <div><div className="stat-num">{collab.activities}</div><div className="stat-lbl">Activities run</div></div>
          <div>
            <div className="stat-num">{collab.learners_grouped}<span className="stat-of">/{learners}</span></div>
            <div className="stat-lbl">Learners who have worked in a group</div>
          </div>
          <div>
            <div className="stat-num">{pct(collab.diversity)}</div>
            <div className="stat-lbl">Groupmate variety, out of the whole class</div>
          </div>
          <div>
            <div className="stat-num">{collab.repeat_pairs}</div>
            <div className="stat-lbl">Pairs who have worked together more than once</div>
          </div>
        </div>
        {collab.never_grouped > 0 && (
          <p className="stat-note">
            <strong>{collab.never_grouped}</strong> learner{collab.never_grouped === 1 ? ' has' : 's have'} not
            been in a group yet.
          </p>
        )}
      </section>

      <div className="card" style={{ background: 'var(--surface-2)' }}>
        <strong>How this works.</strong> <span className="muted">These are class totals for your eyes only.
        Learners never see rankings or each other's numbers, and nothing here diagnoses, grades, or places a student.
        Stars, answers and quests come from the learners' own attempts; confidence and the bands come from the
        learner model described in <code>docs/LEARNER_MODEL.md</code>.</span>
      </div>
    </div>
  )
}
