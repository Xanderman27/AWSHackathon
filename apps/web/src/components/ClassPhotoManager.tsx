// The class blog: the teacher writes a post with a photo, and it appears on the dashboard of
// every family in the class. For most families this is the only picture of the school day
// they get, so the composer is short on purpose — a photo, a headline, a sentence.

import { useEffect, useRef, useState } from 'react'
import { api, getSession } from '../api'
import ClassPhoto from './ClassPhoto'

export interface ClassPhotoRow {
  id: string
  class_id: string
  title: string
  caption: string
  taken_on: string
  uploaded_at: string
  uploaded_by_name: string
  /** Empty for the whole class; a student id when only that learner's family sees it. */
  audience_student_id?: string
  audience_name?: string
}

const MAX_MB = 8

export function localDate(raw: string): Date | null {
  const dateOnly = /^(\d{4})-(\d{2})-(\d{2})$/.exec(raw)
  const when = dateOnly
    ? new Date(Number(dateOnly[1]), Number(dateOnly[2]) - 1, Number(dateOnly[3]))
    : new Date(raw)
  return Number.isNaN(when.getTime()) ? null : when
}

export function photoDate(row: ClassPhotoRow) {
  const when = localDate(row.taken_on || row.uploaded_at)
  return when ? when.toLocaleDateString(undefined, { weekday: 'long', month: 'long', day: 'numeric' }) : ''
}

export default function ClassPhotoManager() {
  const [posts, setPosts] = useState<ClassPhotoRow[] | null>(null)
  const [title, setTitle] = useState('')
  const [caption, setCaption] = useState('')
  const [takenOn, setTakenOn] = useState(() => new Date().toISOString().slice(0, 10))
  const [file, setFile] = useState<File | null>(null)
  const [preview, setPreview] = useState('')
  const [busy, setBusy] = useState(false)
  const [notice, setNotice] = useState('')
  const [error, setError] = useState('')
  // '' means every family in the class; a student id targets that one family.
  const [audience, setAudience] = useState('')
  const [learners, setLearners] = useState<{ id: string; display_name: string }[]>([])
  const fileInput = useRef<HTMLInputElement>(null)

  useEffect(() => {
    api<ClassPhotoRow[]>('/teacher/class-photos')
      .then(setPosts)
      .catch(() => setError('The class blog could not load.'))
    api<{ students: { id: string; display_name: string }[] }>('/teacher/class')
      .then((d) => setLearners(d.students))
      .catch(() => setLearners([]))
  }, [])

  const audienceName = audience ? learners.find((s) => s.id === audience)?.display_name : null

  // Show the teacher what they picked before it goes out to twelve families.
  useEffect(() => {
    if (!file) { setPreview(''); return }
    const url = URL.createObjectURL(file)
    setPreview(url)
    return () => URL.revokeObjectURL(url)
  }, [file])

  function reset() {
    setTitle(''); setCaption(''); setFile(null)
    if (fileInput.current) fileInput.current.value = ''
  }

  async function publish() {
    if (!file) return
    setBusy(true); setError(''); setNotice('')
    try {
      const body = new FormData()
      body.append('file', file)
      body.append('title', title)
      body.append('caption', caption)
      body.append('taken_on', takenOn)
      body.append('audience_student_id', audience)
      const session = getSession()
      const res = await fetch('/api/teacher/class-photos', {
        method: 'POST',
        headers: session ? { 'X-Role': session.role, 'X-User-Id': session.userId } : undefined,
        body,
      })
      if (!res.ok) throw new Error(String(res.status))
      const saved = (await res.json()) as ClassPhotoRow
      setPosts((current) => [saved, ...(current ?? [])])
      reset()
      setNotice(saved.audience_name
        ? `Posted. Only ${saved.audience_name} can see it.`
        : 'Posted. Every family in your class can see it on their dashboard now.')
      setAudience('')
    } catch (problem) {
      setError(
        String(problem).includes('413')
          ? `That photo is larger than ${MAX_MB} MB. Please choose a smaller one.`
          : 'That post could not be published. Try a JPEG, PNG, or WebP image.',
      )
    } finally {
      setBusy(false)
    }
  }

  async function remove(id: string) {
    setError(''); setNotice('')
    try {
      await api(`/teacher/class-photos/${id}`, { method: 'DELETE' })
      setPosts((current) => (current ?? []).filter((row) => row.id !== id))
      setNotice('Removed. It no longer appears for any family.')
    } catch {
      setError('That post could not be removed.')
    }
  }

  return (
    <div className="stack">
      <section className="card blog-composer" aria-labelledby="composer-title">
        <div>
          <span className="chip sky">Families</span>
          <h2 id="composer-title">Write an update</h2>
          <p className="muted">
            Most families see this app between meetings and nothing else. A photo and a sentence
            is often the only picture of the day they get.
          </p>
        </div>

        <div className="composer-body">
          <label className={`composer-drop ${preview ? 'has-photo' : ''}`}>
            {preview
              ? <img src={preview} alt="" className="composer-preview" />
              : <span className="composer-drop-hint"><span aria-hidden="true">📷</span> Choose a photo</span>}
            <span className="visually-hidden">Photo for this update</span>
            <input ref={fileInput} type="file" accept="image/jpeg,image/png,image/webp,image/heic"
              onChange={(event) => setFile(event.target.files?.[0] ?? null)} />
          </label>

          <div className="composer-fields">
            <label className="msg-field">
              <span>Headline</span>
              <input value={title} maxLength={80} placeholder="Three ways to make one half"
                onChange={(event) => setTitle(event.target.value)} />
            </label>
            <label className="msg-field">
              <span>What happened?</span>
              <textarea value={caption} maxLength={600} rows={4}
                placeholder="The teams built the fraction wall together and found three rows that cover the same amount."
                onChange={(event) => setCaption(event.target.value)} />
            </label>
            <label className="msg-field">
              <span>Send to</span>
              <select value={audience} onChange={(event) => setAudience(event.target.value)}>
                <option value="">Every family in the class</option>
                {learners.map((s) => (
                  <option key={s.id} value={s.id}>Only {s.display_name}'s family</option>
                ))}
              </select>
            </label>
            <div className="composer-actions">
              <label className="msg-field composer-date">
                <span>Date</span>
                <input type="date" value={takenOn} onChange={(event) => setTakenOn(event.target.value)} />
              </label>
              <div className="row">
                {file && <button type="button" onClick={reset} disabled={busy}>Discard</button>}
                <button type="button" className="btn-primary btn-lg" disabled={!file || busy} onClick={publish}>
                  {busy ? 'Posting…' : 'Post to families'}
                </button>
              </div>
            </div>
          </div>
        </div>

        <p className="muted photo-audience">
          <strong>Who sees this:</strong> {audienceName
            ? `only ${audienceName}'s family.`
            : 'every family in your class.'} Students never see it, and it is
          not attached to any learner's progress.
        </p>

        {notice && <div className="feedback good" role="status">✓ {notice}</div>}
        {error && <div className="feedback try" role="alert">{error}</div>}
      </section>

      <section aria-labelledby="posts-title">
        <div className="row between" style={{ marginBottom: 12 }}>
          <h2 id="posts-title" style={{ margin: 0 }}>Posted so far</h2>
          {posts && <span className="muted">{posts.length} post{posts.length === 1 ? '' : 's'}</span>}
        </div>

        {posts === null ? <p className="muted">Loading the class blog…</p> : posts.length === 0 ? (
          <div className="card"><p className="muted" style={{ margin: 0 }}>
            Nothing posted yet. The first one goes a long way.
          </p></div>
        ) : (
          <ol className="blog-list">
            {posts.map((post) => (
              <li key={post.id}>
                <article className="card blog-post">
                  <ClassPhoto photoId={post.id} alt={post.title || post.caption || 'A moment from class'} />
                  <div className="blog-body">
                    <p className="blog-date muted">
                      {photoDate(post)}
                      {post.audience_name && <span className="chip cream" style={{ marginLeft: 8 }}>Only {post.audience_name}</span>}
                    </p>
                    {post.title && <h3>{post.title}</h3>}
                    <p className="blog-caption">{post.caption || <span className="muted">No caption</span>}</p>
                    <div className="row between blog-foot">
                      <span className="muted">Posted by {post.uploaded_by_name}</span>
                      <button type="button" className="table-btn" onClick={() => remove(post.id)}>Remove</button>
                    </div>
                  </div>
                </article>
              </li>
            ))}
          </ol>
        )}
      </section>
    </div>
  )
}
