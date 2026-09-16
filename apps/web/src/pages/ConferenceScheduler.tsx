// Parent-facing conference booking: month calendar, time picker, optional agenda (PRD §15).
// Deterministic. No model involved. The teacher still confirms.

import { useEffect, useMemo, useState } from 'react'
import { api } from '../api'

export interface Slot { id: string; start: string; minutes: number; teacher_name: string }
export interface ConfRequest {
  id: string; start: string; minutes: number; agenda: string; status: string; teacher_name: string
}

const DOW = ['Sun', 'Mon', 'Tue', 'Wed', 'Thu', 'Fri', 'Sat']
const MONTHS = ['January', 'February', 'March', 'April', 'May', 'June', 'July', 'August', 'September', 'October', 'November', 'December']

const dayKey = (iso: string) => iso.slice(0, 10)
const fmtTime = (iso: string) =>
  new Date(iso).toLocaleTimeString(undefined, { hour: 'numeric', minute: '2-digit' })
const fmtLong = (iso: string) =>
  new Date(iso).toLocaleDateString(undefined, { weekday: 'long', month: 'long', day: 'numeric' })

const STATUS_TEXT: Record<string, string> = {
  pending: 'Waiting for the teacher to confirm',
  confirmed: 'Confirmed by the teacher',
  declined: 'The teacher could not make this time',
  cancelled: 'You cancelled this request',
}

export default function ConferenceScheduler({ studentId }: { studentId: string }) {
  const [slots, setSlots] = useState<Slot[]>([])
  const [requests, setRequests] = useState<ConfRequest[]>([])
  const [monthStart, setMonthStart] = useState(() => { const d = new Date(); d.setDate(1); return d })
  const [day, setDay] = useState<string | null>(null)
  const [slotId, setSlotId] = useState<string | null>(null)
  const [agenda, setAgenda] = useState('')
  const [busy, setBusy] = useState(false)
  const [error, setError] = useState<string | null>(null)

  const load = () => Promise.all([
    api<Slot[]>('/conferences/slots'),
    api<ConfRequest[]>('/conferences/requests'),
  ]).then(([s, r]) => { setSlots(s); setRequests(r) }).catch((e) => setError(String(e)))

  useEffect(() => { load() }, [])

  const byDay = useMemo(() => {
    const m = new Map<string, Slot[]>()
    for (const s of slots) {
      const k = dayKey(s.start)
      if (!m.has(k)) m.set(k, [])
      m.get(k)!.push(s)
    }
    for (const list of m.values()) list.sort((a, b) => a.start.localeCompare(b.start))
    return m
  }, [slots])

  const active = requests.find((r) => r.status === 'pending' || r.status === 'confirmed')

  const year = monthStart.getFullYear(), month = monthStart.getMonth()
  const firstDow = new Date(year, month, 1).getDay()
  const daysInMonth = new Date(year, month + 1, 0).getDate()
  const cells: (number | null)[] = [
    ...Array(firstDow).fill(null),
    ...Array.from({ length: daysInMonth }, (_, i) => i + 1),
  ]

  async function book() {
    if (!slotId) return
    setBusy(true); setError(null)
    try {
      await api<ConfRequest>('/conferences/requests', {
        method: 'POST',
        body: JSON.stringify({ student_id: studentId, slot_id: slotId, agenda }),
      })
      setDay(null); setSlotId(null); setAgenda('')
      await load()
    } catch (e) {
      setError(String(e).includes('409') ? 'That time was just taken. Please pick another.' : String(e))
      await load()
    } finally {
      setBusy(false)
    }
  }

  async function cancel(id: string) {
    setBusy(true)
    try { await api(`/conferences/requests/${id}`, { method: 'DELETE' }); await load() } finally { setBusy(false) }
  }

  if (active) {
    return (
      <div className="card">
        <h2>Your meeting with {active.teacher_name}</h2>
        <div className="booked">
          <p style={{ fontSize: '1.2em', fontWeight: 600, margin: 0 }}>
            {fmtLong(active.start)} at {fmtTime(active.start)}
          </p>
          <p className="muted" style={{ margin: 0 }}>{active.minutes} minutes</p>
          <p style={{ marginTop: 10 }}>
            <span className={`chip ${active.status === 'confirmed' ? 'mint' : 'cream'}`}>{STATUS_TEXT[active.status]}</span>
          </p>
          {active.agenda && (
            <p className="muted" style={{ marginTop: 6 }}><strong>What you want to talk about:</strong> {active.agenda}</p>
          )}
        </div>
        <button type="button" onClick={() => cancel(active.id)} disabled={busy} style={{ marginTop: 14 }}>
          Cancel this request
        </button>
      </div>
    )
  }

  const times = day ? byDay.get(day) ?? [] : []

  return (
    <div className="card">
      <h2>Talk with the teacher</h2>
      <p className="muted">Pick a time that works for you. Your child's teacher confirms it.</p>
      {error && <p role="alert" className="feedback try" style={{ marginBottom: 14 }}>{error}</p>}

      <div className="grid-2" style={{ alignItems: 'start' }}>
        <div>
          <div className="cal-head">
            <button type="button" className="cal-nav" onClick={() => setMonthStart(new Date(year, month - 1, 1))} aria-label="Previous month">←</button>
            <span className="month" aria-live="polite">{MONTHS[month]} {year}</span>
            <button type="button" className="cal-nav" onClick={() => setMonthStart(new Date(year, month + 1, 1))} aria-label="Next month">→</button>
          </div>
          <div className="cal-grid">
            {DOW.map((d) => <div key={d} className="cal-dow" aria-hidden="true">{d.slice(0, 1)}</div>)}
            {cells.map((n, i) => {
              if (n === null) return <span key={`b${i}`} className="cal-day blank" aria-hidden="true" />
              const key = `${year}-${String(month + 1).padStart(2, '0')}-${String(n).padStart(2, '0')}`
              const count = byDay.get(key)?.length ?? 0
              const label = `${fmtLong(`${key}T12:00`)}, ${count === 0 ? 'no times available' : `${count} time${count > 1 ? 's' : ''} available`}`
              return (
                <button key={key} type="button" className="cal-day" disabled={count === 0}
                  aria-pressed={day === key} aria-label={label}
                  onClick={() => { setDay(key); setSlotId(null) }}>
                  <span aria-hidden="true">{n}</span>
                  <span className="dot" aria-hidden="true" />
                </button>
              )
            })}
          </div>
          <p className="muted" style={{ fontSize: '0.85em', marginTop: 10 }}>A dot means times are open that day.</p>
        </div>

        <div className="stack">
          <div>
            <h3 style={{ marginBottom: 8 }}>{day ? fmtLong(`${day}T12:00`) : 'Pick a day first'}</h3>
            {day ? (
              <div className="times" role="group" aria-label="Available times">
                {times.map((s) => (
                  <button key={s.id} type="button" aria-pressed={slotId === s.id} onClick={() => setSlotId(s.id)}>
                    {fmtTime(s.start)}
                  </button>
                ))}
              </div>
            ) : <p className="muted">Choose a highlighted day on the calendar.</p>}
          </div>
          <div>
            <label htmlFor="agenda" style={{ fontWeight: 600, display: 'block', marginBottom: 6 }}>
              What would you like to talk about? <span className="muted" style={{ fontWeight: 500 }}>(optional)</span>
            </label>
            <textarea id="agenda" value={agenda} maxLength={500} onChange={(e) => setAgenda(e.target.value)}
              placeholder="For example: I'd like ideas for reading at home." />
          </div>
          <div>
            <button type="button" className="btn-primary btn-lg" disabled={!slotId || busy} onClick={book}>
              {busy ? 'Sending…' : 'Request this time'}
            </button>
          </div>
        </div>
      </div>
    </div>
  )
}
