// Activities tab: assign quests, and manage collaborative group activities.
// Group building reuses the shared GroupActivityManager (suggest, edit, publish, end).

import { useEffect, useState } from 'react'
import { api, type Skill } from '../api'
import GroupActivityManager from '../components/GroupActivityManager'
import ClassPhotoManager from '../components/ClassPhotoManager'

interface Assignment { id: string; skill_name: string; subject: string; who: string; at: string }
interface Student { id: string; display_name: string }
interface Summary { students: Student[] }

export default function TeacherActivities() {
  const [skills, setSkills] = useState<Skill[]>([])
  const [students, setStudents] = useState<Student[]>([])
  const [assignments, setAssignments] = useState<Assignment[]>([])
  const [err, setErr] = useState<string | null>(null)

  const [skillId, setSkillId] = useState('')
  const [everyone, setEveryone] = useState(true)
  const [picked, setPicked] = useState<Set<string>>(new Set())
  const [busy, setBusy] = useState(false)
  const [note, setNote] = useState<string | null>(null)

  const load = () => Promise.all([
    api<Skill[]>('/skills'), api<Summary>('/teacher/class'), api<Assignment[]>('/teacher/assignments'),
  ]).then(([sk, cls, asg]) => { setSkills(sk); setStudents(cls.students); setAssignments(asg) })
    .catch((e) => setErr(String(e)))

  useEffect(() => { load() }, [])

  async function assign(e: React.FormEvent) {
    e.preventDefault()
    if (!skillId || busy) return
    setBusy(true); setNote(null)
    try {
      const body = { skill_id: skillId, student_ids: everyone ? null : [...picked] }
      const a = await api<Assignment>('/teacher/assignments', { method: 'POST', body: JSON.stringify(body) })
      setNote(`Assigned "${a.skill_name}" to ${a.who}.`)
      setSkillId(''); setEveryone(true); setPicked(new Set())
      await load()
    } catch {
      setNote('That could not be assigned. Pick a quest, and at least one learner.')
    } finally { setBusy(false) }
  }

  if (err) return <p role="alert">{err}</p>

  return (
    <div className="stack">
      <section className="card">
        <h2>Assign a quest</h2>
        <p className="muted" style={{ marginTop: -6 }}>Assigned quests appear on the learner's Quests tab right away.</p>
        {note && <p role="status" className="feedback good" style={{ padding: '10px 16px', fontSize: '.95em', marginBottom: 12 }}>{note}</p>}
        <form className="stack" style={{ gap: 12 }} onSubmit={assign}>
          <label className="msg-field" style={{ maxWidth: 420 }}>
            <span>Quest</span>
            <select value={skillId} onChange={(e) => setSkillId(e.target.value)} required>
              <option value="">Choose a quest…</option>
              {skills.map((s) => <option key={s.id} value={s.id}>{s.name} ({s.subject})</option>)}
            </select>
          </label>
          <div className="row" role="group" aria-label="Who gets this quest">
            <button type="button" aria-pressed={everyone} onClick={() => setEveryone(true)}>Whole class</button>
            <button type="button" aria-pressed={!everyone} onClick={() => setEveryone(false)}>Chosen learners</button>
          </div>
          {!everyone && (
            <div className="pick-grid" role="group" aria-label="Choose learners">
              {students.map((s) => (
                <button key={s.id} type="button" className="pick" aria-pressed={picked.has(s.id)}
                  onClick={() => setPicked((prev) => { const n = new Set(prev); if (n.has(s.id)) { n.delete(s.id) } else { n.add(s.id) } return n })}>
                  {s.display_name}
                </button>
              ))}
            </div>
          )}
          <div>
            <button type="submit" className="btn-primary" disabled={busy || !skillId || (!everyone && picked.size === 0)}>
              {busy ? 'Assigning…' : 'Assign quest'}
            </button>
          </div>
        </form>

        <h3 style={{ margin: '20px 0 8px', fontSize: '1.05em' }}>Assigned quests</h3>
        {assignments.length === 0 ? <p className="muted">Nothing assigned yet.</p> : (
          <ul className="assign-list">
            {assignments.map((a) => (
              <li key={a.id}>
                <div><strong>{a.skill_name}</strong><span className="muted"> · {a.who}</span></div>
                <button type="button" className="table-btn" onClick={() => api(`/teacher/assignments/${a.id}`, { method: 'DELETE' }).then(load)}>Remove</button>
              </li>
            ))}
          </ul>
        )}
      </section>

      <GroupActivityManager />
      <ClassPhotoManager />
    </div>
  )
}
