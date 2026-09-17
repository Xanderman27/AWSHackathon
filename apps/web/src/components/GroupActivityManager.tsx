import { useCallback, useEffect, useMemo, useState } from 'react'
import { api } from '../api'
import Avatar, { type AvatarSpec } from './Avatar'
import type { GameSpec } from '../games/room'

interface Student {
  id: string
  display_name: string
  evidence_count: number
  photo?: string | null
  avatar?: AvatarSpec | null
}
interface RecommendedGroup { id: string; name: string; member_ids: string[]; rationale: string }

interface Recommendation {
  game_id: string
  title: string
  glyph: string
  teacher_note: string
  uses_evidence: boolean
  method: string
  students: Student[]
  groups: RecommendedGroup[]
  needs_more_evidence: string[]
  student_names: Record<string, string>
}

interface PublishedActivity {
  id: string
  game_id: string
  title: string
  group_name: string
  member_ids: string[]
  published_at: string
}

interface DraftGroup { name: string; member_ids: string[]; rationale: string }

/** What the agent worked out about one group, once it had looked the learners up itself. */
interface Explanation {
  name: string
  why_together: string
  watch_for: string
  origin: string
  inspected: string[]
  turns: number
  warning: string
}

export default function GroupActivityManager() {
  const [catalog, setCatalog] = useState<GameSpec[]>([])
  const [gameId, setGameId] = useState('')
  const [recommendation, setRecommendation] = useState<Recommendation | null>(null)
  const [drafts, setDrafts] = useState<DraftGroup[]>([])
  const [published, setPublished] = useState<PublishedActivity[]>([])
  const [saving, setSaving] = useState(false)
  const [explaining, setExplaining] = useState(false)
  const [explanations, setExplanations] = useState<Record<string, Explanation>>({})
  // Which arrangement the explanations describe. Move a learner and they are stale.
  const [explainedFor, setExplainedFor] = useState('')
  const [notice, setNotice] = useState('')
  const [error, setError] = useState('')

  useEffect(() => {
    Promise.all([
      api<GameSpec[]>('/games'),
      api<PublishedActivity[]>('/teacher/group-activities'),
    ]).then(([games, live]) => {
      setCatalog(games)
      setPublished(live)
      setGameId((current) => current || games[0]?.id || '')
    }).catch(() => setError('Group activities could not load.'))
  }, [])

  // Switching games pulls a fresh suggestion; drafts never carry over between activities.
  useEffect(() => {
    if (!gameId) return
    setRecommendation(null)
    setNotice('')
    api<Recommendation>(`/teacher/group-activities/recommendation?game_id=${gameId}`)
      .then((suggested) => {
        setRecommendation(suggested)
        setDrafts(suggested.groups.map((group) => ({ ...group })))
      })
      .catch(() => setError('Group recommendations could not load.'))
  }, [gameId])

  const assignment = useMemo(() => {
    const result: Record<string, number> = {}
    drafts.forEach((group, index) => group.member_ids.forEach((studentId) => { result[studentId] = index }))
    return result
  }, [drafts])

  // A signature of the current arrangement, so we can tell when an explanation stops matching.
  const arrangement = useMemo(
    () => drafts.filter((g) => g.member_ids.length > 0)
      .map((g) => `${g.name}:${[...g.member_ids].sort().join(',')}`).join('|'),
    [drafts],
  )
  const stale = explainedFor !== '' && explainedFor !== arrangement

  const spec = catalog.find((game) => game.id === gameId)
  const minGroup = spec?.min_group ?? 2
  const maxGroup = spec?.max_group ?? 4
  const withMembers = drafts.filter((group) => group.member_ids.length > 0)
  const canPublish = withMembers.length > 0
    && withMembers.every((group) => group.member_ids.length >= minGroup && group.member_ids.length <= maxGroup)
  const liveForThisGame = published.filter((activity) => activity.game_id === gameId)
  const publishedGameIds = new Set(published.map((activity) => activity.game_id))

  function moveStudent(studentId: string, target: string) {
    setNotice('')
    setDrafts((current) => {
      const next = current.map((group) => ({ ...group, member_ids: group.member_ids.filter((id) => id !== studentId) }))
      if (target !== '') next[Number(target)].member_ids.push(studentId)
      return next
    })
  }

  function renameGroup(index: number, name: string) {
    setDrafts((current) => current.map((group, i) => (i === index ? { ...group, name } : group)))
  }

  const explainGroups = useCallback(async () => {
    setExplaining(true); setError('')
    try {
      const response = await api<{ groups: Explanation[] }>('/teacher/group-activities/explain', {
        method: 'POST',
        body: JSON.stringify({
          game_id: gameId,
          groups: withMembers.map(({ name, member_ids }) => ({ name, member_ids })),
        }),
      })
      setExplanations(Object.fromEntries(response.groups.map((group) => [group.name, group])))
      setExplainedFor(arrangement)
    } catch {
      // The suggestion itself still stands; only the prose is missing.
      setError('The explanation could not be generated. The grouping itself is unaffected.')
    } finally {
      setExplaining(false)
    }
  }, [gameId, arrangement])

  // Explain as soon as there is something to explain. A teacher should not have to know to
  // ask: before this, the canned sentence read like the whole rationale.
  useEffect(() => {
    if (!gameId || !arrangement || explaining) return
    if (explainedFor === arrangement) return
    if (explainedFor === '') void explainGroups()
  }, [gameId, arrangement, explainedFor, explaining, explainGroups])

  // Switching activity throws away the previous activity's explanations.
  useEffect(() => { setExplanations({}); setExplainedFor('') }, [gameId])

  async function publishGroups() {
    setSaving(true); setError(''); setNotice('')
    try {
      const response = await api<{ activities: PublishedActivity[] }>('/teacher/group-activities/publish', {
        method: 'POST',
        body: JSON.stringify({ game_id: gameId, groups: withMembers }),
      })
      setPublished((current) => [...current.filter((a) => a.game_id !== gameId), ...response.activities])
      setNotice('Published. Each learner can now see only their assigned group activity.')
    } catch {
      setError(`The groups could not be published. Check that every group has ${minGroup}–${maxGroup} learners.`)
    } finally {
      setSaving(false)
    }
  }

  async function unpublish() {
    setSaving(true); setError(''); setNotice('')
    try {
      await api<{ activities: PublishedActivity[] }>(`/teacher/group-activities/${gameId}`, { method: 'DELETE' })
      setPublished((current) => current.filter((activity) => activity.game_id !== gameId))
      setNotice('Taken down. This activity no longer appears for any learner.')
    } catch {
      setError('The groups could not be taken down.')
    } finally {
      setSaving(false)
    }
  }

  if (error && !catalog.length) return <div className="card feedback try" role="alert">{error}</div>
  if (!catalog.length) return <div className="card"><p style={{ margin: 0 }}>Loading collaborative activities…</p></div>

  return (
    <section className="card group-manager" aria-labelledby="group-manager-title">
      <div className="row between">
        <div>
          <span className="chip mint">Collaborative activities</span>
          <h2 id="group-manager-title">Group learners for an activity</h2>
          <p className="muted">Pick an activity, review the suggestion, move learners if needed, then publish.</p>
        </div>
        <span className="teacher-game-icon" aria-hidden="true">{spec?.glyph ?? '🎲'}</span>
      </div>

      <div className="game-picker" role="group" aria-label="Choose a collaborative activity">
        {catalog.map((game) => (
          <button type="button" key={game.id} aria-pressed={game.id === gameId}
            className={`game-pick ${game.tone}`} onClick={() => setGameId(game.id)}>
            <span className="game-pick-glyph" aria-hidden="true">{game.glyph}</span>
            <span className="game-pick-text">
              <strong>{game.title}</strong>
              <small>{game.skill_hint}</small>
            </span>
            {publishedGameIds.has(game.id) && <span className="chip mint game-pick-live">live</span>}
          </button>
        ))}
      </div>

      {!recommendation ? (
        <p className="muted">Building group recommendations…</p>
      ) : (
        <>
          <div className="recommendation-note">
            <strong>How the platform recommended these groups</strong>
            <span>{recommendation.method}</span>
            {recommendation.teacher_note && <span>{recommendation.teacher_note}</span>}
            <span>Goal links, disability status, demographics, and behavior are never inputs.</span>
          </div>

          <div className="draft-group-grid">
            {drafts.map((group, index) => (
              <div className="draft-group" key={index}>
                <label>
                  <span className="visually-hidden">Name for group {index + 1}</span>
                  <input value={group.name} maxLength={40} onChange={(event) => renameGroup(index, event.target.value)} />
                </label>
                <ul className="draft-members">
                  {group.member_ids.map((studentId) => {
                    const learner = recommendation.students.find((s) => s.id === studentId)
                    return (
                      <li key={studentId}>
                        <Avatar photo={learner?.photo} spec={learner?.avatar} size={38} />
                        <span>{recommendation.student_names[studentId]}</span>
                      </li>
                    )
                  })}
                  {group.member_ids.length === 0 && <li className="muted">No learners assigned</li>}
                </ul>
                {explaining && !explanations[group.name] ? (
                  <p className="muted agent-thinking">Working out why these three fit together…</p>
                ) : explanations[group.name] ? (
                  <div className="group-explained">
                    <p className="why">{explanations[group.name].why_together}</p>
                    <p className="watch"><strong>Watch for:</strong> {explanations[group.name].watch_for}</p>
                    <p className="agent-trace muted">
                      {stale ? 'groups have changed since this was written' :
                        explanations[group.name].origin === 'bedrock'
                          ? `agent checked ${explanations[group.name].inspected.join(', ')} · ${explanations[group.name].turns} steps`
                          : explanations[group.name].warning || 'standard explanation'}
                    </p>
                  </div>
                ) : (
                  <p>{group.rationale}</p>
                )}
                <span className={`group-size ${group.member_ids.length > 0 && group.member_ids.length < minGroup ? 'warn' : ''}`}>
                  {group.member_ids.length} learner{group.member_ids.length === 1 ? '' : 's'} · {minGroup}–{maxGroup} needed
                </span>
              </div>
            ))}
            {drafts.length === 0 && (
              <p className="muted">
                No learner has enough evidence for this activity yet. Ask the class to finish a quest first, or pick an
                activity that does not read from an objective.
              </p>
            )}
          </div>

          <div className="cohort-roster">
            <h3>Adjust the groups</h3>
            <p className="muted">Every change is teacher-controlled. “Not assigned” keeps the activity off that learner’s screen.</p>
            <div className="table-scroll">
              <table>
                <thead>
                  <tr>
                    <th>Learner</th>
                    <th>{recommendation.uses_evidence ? 'Relevant evidence' : 'Evidence used'}</th>
                    <th>Activity group</th>
                  </tr>
                </thead>
                <tbody>
                  {recommendation.students.map((student) => (
                    <tr key={student.id}>
                      <td className="learner-cell">
                        <Avatar photo={student.photo} spec={student.avatar} size={36} className="avatar-img" />
                        {student.display_name}
                      </td>
                      <td>
                        {!recommendation.uses_evidence
                          ? <span className="muted">None · free play</span>
                          : recommendation.needs_more_evidence.includes(student.id)
                            ? <span className="chip cream">Needs more evidence</span>
                            : `${student.evidence_count} recent items`}
                      </td>
                      <td>
                        <select aria-label={`Group for ${student.display_name}`} value={assignment[student.id] ?? ''}
                          onChange={(event) => moveStudent(student.id, event.target.value)}>
                          <option value="">Not assigned</option>
                          {drafts.map((group, index) => (
                            <option value={index} key={index}
                              disabled={group.member_ids.length >= maxGroup && assignment[student.id] !== index}>
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
              {liveForThisGame.length > 0 && (
                <strong>{liveForThisGame.length} group{liveForThisGame.length === 1 ? '' : 's'} published for {recommendation.title}</strong>
              )}
              <p className="muted">Students see their team and a single Join activity button—never the recommendation rationale.</p>
            </div>
            <div className="row">
              {liveForThisGame.length > 0 && (
                <button type="button" disabled={saving} onClick={unpublish}>Take down</button>
              )}
              <button type="button" disabled={explaining || withMembers.length === 0}
                onClick={explainGroups}
                title="An agent looks up each learner's evidence, then explains the pairing">
                {explaining ? 'Thinking…' : stale ? 'Update explanations' : 'Explain again'}
              </button>
              <button className="btn-primary btn-lg" type="button" disabled={!canPublish || saving} onClick={publishGroups}>
                {saving ? 'Publishing…' : liveForThisGame.length ? 'Update published groups' : 'Publish to students'}
              </button>
            </div>
          </div>
        </>
      )}
      {notice && <div className="feedback good" role="status">✓ {notice}</div>}
      {error && <div className="feedback try" role="alert">{error}</div>}
    </section>
  )
}
