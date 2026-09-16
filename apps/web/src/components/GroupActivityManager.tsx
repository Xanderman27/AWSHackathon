import { useEffect, useMemo, useState } from 'react'
import { api } from '../api'

interface Student {
  id: string
  display_name: string
  evidence_count: number
}

interface RecommendedGroup {
  id: string
  name: string
  member_ids: string[]
  rationale: string
}

interface Recommendation {
  game_id: string
  title: string
  method: string
  students: Student[]
  groups: RecommendedGroup[]
  needs_more_evidence: string[]
  student_names: Record<string, string>
}

interface PublishedActivity {
  id: string
  title: string
  group_name: string
  member_ids: string[]
  published_at: string
}

interface DraftGroup {
  name: string
  member_ids: string[]
  rationale: string
}

export default function GroupActivityManager() {
  const [recommendation, setRecommendation] = useState<Recommendation | null>(null)
  const [drafts, setDrafts] = useState<DraftGroup[]>([])
  const [published, setPublished] = useState<PublishedActivity[]>([])
  const [saving, setSaving] = useState(false)
  const [notice, setNotice] = useState('')
  const [error, setError] = useState('')

  useEffect(() => {
    Promise.all([
      api<Recommendation>('/teacher/group-activities/recommendation'),
      api<PublishedActivity[]>('/teacher/group-activities'),
    ]).then(([suggested, live]) => {
      setRecommendation(suggested)
      setDrafts(suggested.groups.map((group) => ({
        name: group.name,
        member_ids: group.member_ids,
        rationale: group.rationale,
      })))
      setPublished(live)
    }).catch(() => setError('Group recommendations could not load.'))
  }, [])

  const assignment = useMemo(() => {
    const result: Record<string, number> = {}
    drafts.forEach((group, groupIndex) => group.member_ids.forEach((studentId) => { result[studentId] = groupIndex }))
    return result
  }, [drafts])

  const groupsWithMembers = drafts.filter((group) => group.member_ids.length > 0)
  const canPublish = groupsWithMembers.length > 0 && groupsWithMembers.every((group) => group.member_ids.length >= 2 && group.member_ids.length <= 4)

  function moveStudent(studentId: string, target: string) {
    setNotice('')
    setDrafts((current) => {
      const next = current.map((group) => ({ ...group, member_ids: group.member_ids.filter((id) => id !== studentId) }))
      if (target !== '') next[Number(target)].member_ids.push(studentId)
      return next
    })
  }

  function renameGroup(groupIndex: number, name: string) {
    setDrafts((current) => current.map((group, index) => index === groupIndex ? { ...group, name } : group))
  }

  async function publishGroups() {
    setSaving(true)
    setError('')
    setNotice('')
    try {
      const response = await api<{ activities: PublishedActivity[] }>('/teacher/group-activities/publish', {
        method: 'POST',
        body: JSON.stringify({ groups: groupsWithMembers }),
      })
      setPublished(response.activities)
      setNotice('Published. Each learner can now see only their assigned group activity.')
    } catch {
      setError('The groups could not be published. Check that every group has 2–4 learners.')
    } finally {
      setSaving(false)
    }
  }

  if (error && !recommendation) return <div className="card feedback try" role="alert">{error}</div>
  if (!recommendation) return <div className="card"><p style={{ margin: 0 }}>Building group recommendations…</p></div>

  return (
    <section className="card group-manager" aria-labelledby="group-manager-title">
      <div className="row between">
        <div>
          <span className="chip mint">Collaborative activity</span>
          <h2 id="group-manager-title">Create Beat Together groups</h2>
          <p className="muted">Review the platform suggestion, move learners if needed, then publish.</p>
        </div>
        <span className="teacher-game-icon" aria-hidden="true">🎵</span>
      </div>

      <div className="recommendation-note">
        <strong>How the platform recommended these groups</strong>
        <span>{recommendation.method}</span>
        <span>Goal links, disability status, demographics, and behavior are never inputs.</span>
      </div>

      <div className="draft-group-grid">
        {drafts.map((group, groupIndex) => (
          <div className="draft-group" key={groupIndex}>
            <label>
              <span className="visually-hidden">Name for group {groupIndex + 1}</span>
              <input value={group.name} maxLength={40} onChange={(event) => renameGroup(groupIndex, event.target.value)} />
            </label>
            <div className="draft-members">
              {group.member_ids.map((studentId) => <span className="chip sky" key={studentId}>{recommendation.student_names[studentId]}</span>)}
              {group.member_ids.length === 0 && <span className="muted">No learners assigned</span>}
            </div>
            <p>{group.rationale}</p>
            <span className={`group-size ${group.member_ids.length > 0 && group.member_ids.length < 2 ? 'warn' : ''}`}>
              {group.member_ids.length} learner{group.member_ids.length === 1 ? '' : 's'} · 2–4 needed
            </span>
          </div>
        ))}
      </div>

      <div className="cohort-roster">
        <h3>Adjust the groups</h3>
        <p className="muted">Every change is teacher-controlled. “Not assigned” keeps the activity off that learner’s screen.</p>
        <div className="table-scroll">
          <table>
            <thead><tr><th>Learner</th><th>Relevant evidence</th><th>Activity group</th></tr></thead>
            <tbody>
              {recommendation.students.map((student) => (
                <tr key={student.id}>
                  <td><span className="avatar" aria-hidden="true">{student.display_name[0]}</span>{student.display_name}</td>
                  <td>
                    {recommendation.needs_more_evidence.includes(student.id)
                      ? <span className="chip cream">Needs more evidence</span>
                      : `${student.evidence_count} recent items`}
                  </td>
                  <td>
                    <select aria-label={`Group for ${student.display_name}`} value={assignment[student.id] ?? ''}
                      onChange={(event) => moveStudent(student.id, event.target.value)}>
                      <option value="">Not assigned</option>
                      {drafts.map((group, index) => (
                        <option value={index} key={index} disabled={group.member_ids.length >= 4 && assignment[student.id] !== index}>
                          {group.name || `Group ${index + 1}`}
                        </option>
                      ))}
                    </select>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </div>

      <div className="publish-row">
        <div>
          {published.length > 0 && <strong>{published.length} group{published.length === 1 ? '' : 's'} currently published</strong>}
          <p className="muted">Students see their team and a single Join activity button—never the recommendation rationale.</p>
        </div>
        <button className="btn-primary btn-lg" type="button" disabled={!canPublish || saving} onClick={publishGroups}>
          {saving ? 'Publishing…' : published.length ? 'Update published groups' : 'Publish to students'}
        </button>
      </div>
      {notice && <div className="feedback good" role="status">✓ {notice}</div>}
      {error && <div className="feedback try" role="alert">{error}</div>}
    </section>
  )
}
