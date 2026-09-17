// Thin API client. Role and user come from the synthetic session (PRD FR-01); Cognito later.

export type Role = 'student' | 'teacher' | 'parent'

export interface Session {
  role: Role
  userId: string
  name?: string
  /** The signed token every request is authorised by. Without it the API answers 401:
      role and user id are read from the token's claims, never from what we send. */
  token: string
  refreshToken?: string
}

const KEY = 'alp.session'

export function getSession(): Session | null {
  try {
    const raw = localStorage.getItem(KEY)
    if (!raw) return null
    const parsed = JSON.parse(raw) as Session
    // A session stored before tokens existed has no token, and the API will refuse it.
    // Treat it as signed out rather than letting the app run into 401s on every screen.
    return parsed?.token ? parsed : null
  } catch {
    return null
  }
}

export function setSession(s: Session | null) {
  try {
    if (s) localStorage.setItem(KEY, JSON.stringify(s))
    else localStorage.removeItem(KEY)
  } catch {
    /* storage unavailable; session lives in memory only */
  }
}

export async function api<T>(path: string, init: RequestInit = {}): Promise<T> {
  const s = getSession()
  const headers: Record<string, string> = { 'Content-Type': 'application/json', ...(init.headers as Record<string, string>) }
  if (s?.token) headers['Authorization'] = `Bearer ${s.token}`
  const res = await fetch(`/api${path}`, { ...init, headers })
  if (res.status === 401) {
    // The token expired or was rejected. Drop it rather than retrying with something the
    // server has already refused, and let the app send them back to the door.
    setSession(null)
    window.dispatchEvent(new CustomEvent('dori:signed-out'))
    throw new Error('401 signed out')
  }
  if (!res.ok) throw new Error(`${res.status} ${await res.text()}`)
  return res.json() as Promise<T>
}

/** What both sign-in and sign-up hand back. The token is the part that matters. */
interface AuthResponse {
  role: Role; user_id: string; display_name: string
  token: string; refresh_token?: string; expires_in: number
}

export async function login(username: string, password: string): Promise<Session> {
  const res = await fetch('/api/auth/login', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ username, password }),
  })
  if (!res.ok) throw new Error(res.status === 401 ? 'bad-credentials' : `${res.status}`)
  const d = (await res.json()) as AuthResponse
  const s: Session = { role: d.role, userId: d.user_id, name: d.display_name,
    token: d.token, refreshToken: d.refresh_token }
  setSession(s)
  return s
}

export interface SignUpResult extends Session { class_name: string; needs_child: boolean }

/** Create a family account from a class code, and sign them straight in. */
export async function signUp(input: { name: string; email: string; password: string; classCode: string }): Promise<SignUpResult> {
  const res = await fetch('/api/auth/signup', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({
      name: input.name, email: input.email, password: input.password, class_code: input.classCode,
    }),
  })
  if (!res.ok) {
    const detail = await res.json().catch(() => null)
    throw new Error(detail?.detail ?? 'We could not create that account. Please try again.')
  }
  const d = (await res.json()) as AuthResponse & { class_name: string; needs_child: boolean }
  const session: Session = { role: d.role, userId: d.user_id, name: d.display_name,
    token: d.token, refreshToken: d.refresh_token }
  setSession(session)
  return { ...session, class_name: d.class_name, needs_child: d.needs_child }
}

/** Fetch bytes rather than JSON, carrying the same bearer token every other call does. */
export async function apiBlob(path: string): Promise<Blob> {
  const session = getSession()
  const headers: Record<string, string> = {}
  if (session?.token) headers['Authorization'] = `Bearer ${session.token}`
  const res = await fetch(`/api${path}`, { headers })
  if (!res.ok) throw new Error(`${res.status}`)
  return res.blob()
}

export interface Choice { id: string; text: string }
export interface Item {
  id: string; prompt: string; image_alt?: string | null; choices: Choice[]; hint: string
  passage?: string | null; passage_read_aloud_allowed: boolean
}
export interface NextItem { attempt_id: string; position: number; total: number; item: Item | null; completed: boolean; summary?: string | null }
export interface AnswerOut { correct: boolean; feedback: string; next: NextItem }
export interface Skill { id: string; name: string; child_name: string; subject: string; standard_id: string }
