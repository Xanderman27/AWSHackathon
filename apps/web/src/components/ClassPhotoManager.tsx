// The teacher's side of the family photo feed: pick a photo, say what it was, share it.
// Everything here goes to every family in the class, so the panel says so plainly rather
// than leaving the teacher to guess who will see it.

import { useEffect, useRef, useState } from 'react'
import { api, getSession } from '../api'
import ClassPhoto from './ClassPhoto'

export interface ClassPhotoRow {
  id: string
  class_id: string
  caption: string
  taken_on: string
  uploaded_at: string
  uploaded_by_name: string
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
  const [photos, setPhotos] = useState<ClassPhotoRow[] | null>(null)
  const [caption, setCaption] = useState('')
  const [takenOn, setTakenOn] = useState(() => new Date().toISOString().slice(0, 10))
  const [file, setFile] = useState<File | null>(null)
  const [busy, setBusy] = useState(false)
  const [notice, setNotice] = useState('')
  const [error, setError] = useState('')
  const fileInput = useRef<HTMLInputElement>(null)

  useEffect(() => {
    api<ClassPhotoRow[]>('/teacher/class-photos')
      .then(setPhotos)
      .catch(() => setError('Classroom photos could not load.'))
  }, [])

  async function share() {
    if (!file) return
    setBusy(true); setError(''); setNotice('')
    try {
      const body = new FormData()
      body.append('file', file)
      body.append('caption', caption)
      body.append('taken_on', takenOn)
      const session = getSession()
      const res = await fetch('/api/teacher/class-photos', {
        method: 'POST',
        headers: session ? { 'X-Role': session.role, 'X-User-Id': session.userId } : undefined,
        body,
      })
      if (!res.ok) throw new Error(await res.text())
      const saved = (await res.json()) as ClassPhotoRow
      setPhotos((current) => [saved, ...(current ?? [])])
      setCaption(''); setFile(null)
      if (fileInput.current) fileInput.current.value = ''
      setNotice('Shared. Every family in your class can see it on their dashboard now.')
    } catch (problem) {
      setError(
        String(problem).includes('413')
          ? `That photo is larger than ${MAX_MB} MB. Please choose a smaller one.`
          : 'That photo could not be shared. Try a JPEG, PNG, or WebP image.',
      )
    } finally {
      setBusy(false)
    }
  }

  async function remove(id: string) {
    setError(''); setNotice('')
    try {
      await api(`/teacher/class-photos/${id}`, { method: 'DELETE' })
      setPhotos((current) => (current ?? []).filter((row) => row.id !== id))
      setNotice('Removed. It no longer appears for any family.')
    } catch {
      setError('That photo could not be removed.')
    }
  }

  return (
    <section className="card photo-manager" aria-labelledby="photo-manager-title">
      <div className="row between">
        <div>
          <span className="chip sky">Families</span>
          <h2 id="photo-manager-title">Share a moment from class</h2>
          <p className="muted">
            A photo and a sentence reach every family in your class. Most families see the app
            between meetings and nothing else, so this is often the only picture of the day they get.
          </p>
        </div>
        <span className="teacher-game-icon" aria-hidden="true">📸</span>
      </div>

      <div className="photo-upload">
        <label className="photo-file">
          <span>Photo</span>
          <input ref={fileInput} type="file" accept="image/jpeg,image/png,image/webp,image/heic"
            onChange={(event) => setFile(event.target.files?.[0] ?? null)} />
        </label>
        <label className="photo-caption">
          <span>What was happening?</span>
          <input value={caption} maxLength={280} placeholder="Fraction strips day — the teams found three ways to make one half."
            onChange={(event) => setCaption(event.target.value)} />
        </label>
        <label className="photo-date">
          <span>Date</span>
          <input type="date" value={takenOn} onChange={(event) => setTakenOn(event.target.value)} />
        </label>
        <button type="button" className="btn-primary btn-lg" disabled={!file || busy} onClick={share}>
          {busy ? 'Sharing…' : 'Share with families'}
        </button>
      </div>

      <p className="muted photo-audience">
        <strong>Who sees this:</strong> every family in class 4A. Students never see it, and it is
        not attached to any learner's progress.
      </p>

      {notice && <div className="feedback good" role="status">✓ {notice}</div>}
      {error && <div className="feedback try" role="alert">{error}</div>}

      {photos === null ? <p className="muted">Loading shared photos…</p> : (
        <div className="photo-grid">
          {photos.map((row) => (
            <figure className="photo-tile" key={row.id}>
              <ClassPhoto photoId={row.id} alt={row.caption || 'A moment from class'} />
              <figcaption>
                <strong>{photoDate(row)}</strong>
                <span>{row.caption || 'No caption'}</span>
                <button type="button" className="table-btn" onClick={() => remove(row.id)}>Remove</button>
              </figcaption>
            </figure>
          ))}
          {photos.length === 0 && <p className="muted">Nothing shared yet. The first photo goes a long way.</p>}
        </div>
      )}
    </section>
  )
}
