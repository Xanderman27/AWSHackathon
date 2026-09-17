// The parent home, shaped like a Duolingo profile: identity up top, a statistics grid,
// achievements with progress, the child's group activities, then the mastery detail.

import { useEffect, useState, type ComponentType } from 'react'
import { api } from '../api'
import { OutcomeTrack } from '../components/MasteryGauge'
import { FamilySupport } from '../components/Support'
import Avatar, { type AvatarSpec } from '../components/Avatar'
import ClassPhoto from '../components/ClassPhoto'
import JoinClass from '../components/JoinClass'
import { localDate, photoDate, type ClassPhotoRow } from '../components/ClassPhotoManager'
import {
  BoltIcon, BulbIcon, FlagIcon, GlobeIcon, StarIcon, TeamIcon, TreasureMapIcon,
} from '../components/PathArt'

interface Child { id: string; display_name: string; grade: number; photo?: string | null; avatar?: AvatarSpec | null }
interface NextStep {
  id: string; title: string; why: string; minutes: number
  materials: string[]; steps: string[]; approved_by: string; approved_on: string
}
interface MasteryRow {
  skill_id: string; skill: string; child_name: string; estimate: number; score: number
  band: string; band_label: string; evidence_count: number; history: number[]
}
interface Achievement { id: string; title: string; desc: string; icon: string; progress: number; goal: number; earned: boolean }
interface Teammate { id: string; display_name: string; photo?: string | null; avatar?: AvatarSpec | null }
interface GroupActivity {
  id: string
  title: string
  group_name: string
  published_at?: string | null
  teammates: Teammate[]
}
interface Progress {
  student: Child
  what_we_practiced: { skill: string; practiced: string; sessions: number }[]
  next_steps: NextStep[]
  mastery: MasteryRow[]
  average_score: number | null
  stats: { stars: number; checkins: number; quests_done: number; subjects: number; hints: number; group_count: number }
  achievements: Achievement[]
  group_activities: GroupActivity[]
}

const BAND_TONE: Record<string, string> = { building: 'cream', practicing: 'sky', extension: 'mint' }
const ACH_ICON: Record<string, ComponentType<{ size?: number }>> = {
  flag: FlagIcon, star: StarIcon, map: TreasureMapIcon, bolt: BoltIcon, team: TeamIcon, bulb: BulbIcon,
}
const ACH_TONE = ['#ffc800', '#1cb0f6', '#58cc02', '#ce82ff', '#ff8fab', '#ffb020']

function activityDate(raw: string) {
  const when = localDate(raw)
  return when ? when.toLocaleDateString(undefined, { month: 'long', day: 'numeric' }) : ''
}

export default function ParentProgress() {
  const [children, setChildren] = useState<Child[] | null>(null)
  const [progress, setProgress] = useState<Progress | null>(null)
  const [err, setErr] = useState<string | null>(null)
  const [photos, setPhotos] = useState<ClassPhotoRow[]>([])

  useEffect(() => {
    api<Child[]>('/parent/children')
      .then((c) => { setChildren(c); if (c[0]) return api<Progress>(`/parent/children/${c[0].id}/progress`).then(setProgress) })
      .catch((e) => setErr(String(e)))
    // The classroom feed is about the class, not one child, so it loads independently.
    api<ClassPhotoRow[]>('/parent/class-photos').then(setPhotos).catch(() => setPhotos([]))
  }, [])

  if (err) return <p role="alert">{err}</p>
  if (children !== null && children.length === 0) {
    return (
      <section className="card join-card">
        <JoinClass onJoined={() => window.location.reload()} />
      </section>
    )
  }
  if (!progress) return <p>Loading…</p>

  const { student, mastery, stats, achievements, group_activities: groups } = progress

  const STATS = [
    { label: 'Stars on the path', value: stats.stars, Icon: StarIcon },
    { label: 'Questions answered', value: stats.checkins, Icon: BoltIcon },
    { label: 'Quests finished', value: stats.quests_done, Icon: FlagIcon },
    { label: 'Subjects explored', value: stats.subjects, Icon: GlobeIcon },
  ]

  return (
    <div className="stack">
      {(children?.length ?? 0) > 1 && (
        <div className="row" role="group" aria-label="Choose a child">
          {(children ?? []).map((c) => (
            <button key={c.id} type="button" aria-pressed={student.id === c.id}
              onClick={() => api<Progress>(`/parent/children/${c.id}/progress`).then(setProgress)}>
              {c.display_name}
            </button>
          ))}
        </div>
      )}

      {photos.length > 0 && (
        <section className="card classroom-feed" aria-labelledby="feed-title">
          <div className="row between">
            <div>
              <h3 className="profile-sub" id="feed-title" style={{ marginTop: 0 }}>From the classroom</h3>
              <p className="muted" style={{ margin: 0 }}>
                Shared by {photos[0].uploaded_by_name} with the families in {student.display_name}'s class.
              </p>
            </div>
          </div>
          <div className="feed-strip">
            {photos.map((row) => (
              <figure className="feed-item" key={row.id}>
                <ClassPhoto photoId={row.id} alt={row.caption || 'A moment from class'} />
                <figcaption>
                  <span className="feed-date muted">
                    {photoDate(row)}
                    {row.audience_student_id && <span className="chip cream" style={{ marginLeft: 8 }}>Just for your family 💛</span>}
                  </span>
                  {row.title && <strong>{row.title}</strong>}
                  <span>{row.caption}</span>
                </figcaption>
              </figure>
            ))}
          </div>
        </section>
      )}

      <div className="profile-head">
        <Avatar photo={student.photo} spec={student.avatar} size={76} className="profile-avatar" />
        <div>
          <h2 style={{ marginBottom: 2 }}>{student.display_name}</h2>
          <p className="muted" style={{ margin: 0 }}>Grade {student.grade}</p>
        </div>
      </div>

      <section>
        <h3 className="profile-sub">Statistics</h3>
        <div className="stat-grid">
          {STATS.map(({ label, value, Icon }) => (
            <div className="stat-card" key={label}>
              <Icon size={34} />
              <div><div className="stat-num">{value}</div><div className="stat-lbl">{label}</div></div>
            </div>
          ))}
        </div>
      </section>

      <div className="grid-2" style={{ alignItems: 'start' }}>
        <section className="card">
          <h3 className="profile-sub" style={{ marginTop: 0 }}>Achievements</h3>
          <div className="ach-list">
            {achievements.map((a, i) => {
              const Icon = ACH_ICON[a.icon] ?? StarIcon
              const pct = Math.round((a.progress / a.goal) * 100)
              return (
                <div className={`ach ${a.earned ? 'earned' : ''}`} key={a.id}>
                  <span className="ach-badge" style={{ background: ACH_TONE[i % ACH_TONE.length] }}><Icon size={30} /></span>
                  <div className="ach-body">
                    <div className="row between"><strong>{a.title}</strong>
                      <span className="muted" style={{ fontSize: '.82em' }}>{a.earned ? 'Earned!' : `${a.progress}/${a.goal}`}</span>
                    </div>
                    <span className="muted" style={{ fontSize: '.88em' }}>{a.desc}</span>
                    <span className="ach-bar" role="img" aria-label={`${pct} percent complete`}><i style={{ width: `${pct}%` }} /></span>
                  </div>
                </div>
              )
            })}
          </div>
        </section>

        <div className="stack">
          <section className="card">
            <h3 className="profile-sub" style={{ marginTop: 0 }}>Who {student.display_name} works with</h3>
            {groups.length === 0 ? (
              <p className="muted" style={{ margin: 0 }}>{student.display_name} has not joined a team activity yet.</p>
            ) : groups.map((g) => (
              <div className="group-row teamed" key={g.id}>
                <span className="ach-badge" style={{ background: '#1cb0f6' }}><TeamIcon size={30} /></span>
                <div>
                  <strong>{g.title}</strong>
                  <p className="muted" style={{ margin: '2px 0 0', fontSize: '.9em' }}>
                    {g.group_name}{g.published_at ? ` · since ${activityDate(g.published_at)}` : ''}
                  </p>
                  <ul className="team-strip">
                    {g.teammates.map((mate) => (
                      <li key={mate.id}>
                        <Avatar photo={mate.photo} spec={mate.avatar} size={44} />
                        <span>{mate.display_name}</span>
                      </li>
                    ))}
                  </ul>
                </div>
              </div>
            ))}
          </section>

        </div>
      </div>

      <section className="card">
        <h3 className="profile-sub" style={{ marginTop: 0 }}>Primary outcomes</h3>
        {mastery.length === 0 ? (
          <p className="muted">{student.display_name} has not started a quest yet, so there is nothing to show.</p>
        ) : mastery.map((m) => (
          <div className="outcome" key={m.skill_id}>
            <div className="outcome-head">
              <strong>{student.display_name} can work on {m.child_name}</strong>
              <span className={`chip ${BAND_TONE[m.band]}`}>{m.band_label}</span>
            </div>
            <OutcomeTrack score={m.score} band={m.band_label} evidence={m.evidence_count} />
            <span className="muted" style={{ fontSize: '.85em' }}>Based on {m.evidence_count} check-in{m.evidence_count === 1 ? '' : 's'}</span>
          </div>
        ))}
      </section>

      <FamilySupport studentId={student.id} studentName={student.display_name} />
    </div>
  )
}
