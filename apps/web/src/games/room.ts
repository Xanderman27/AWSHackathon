// Shared client for every collaborative activity. One socket, one snapshot, one send().
// The server owns the state; this file never guesses what the board looks like.

import { useEffect, useRef, useState } from 'react'
import { api, getSession } from '../api'
import type { AvatarSpec } from '../components/Avatar'

export interface Participant {
  id: string
  name: string
  color: string
  photo?: string | null
  avatar?: AvatarSpec | null
}

/** One seat in a group: the learner, whether or not they are currently in the room. */
export interface Member {
  id: string
  display_name: string
  photo?: string | null
  avatar?: AvatarSpec | null
  is_you: boolean
}

export interface RoomSnapshot<S> {
  type: 'state'
  room_id: string
  game_id: string
  revision: number
  state: S
  participants: Participant[]
  /** Teammates' live pointers, normalized 0..1 over the shared play surface. */
  cursors?: Record<string, [number, number]>
}

export type Connection = 'connecting' | 'live' | 'lost'

export interface GameSpec {
  id: string
  title: string
  glyph: string
  tone: string
  blurb: string
  instructions: string
  skill_hint: string
  min_group: number
  max_group: number
  solo: boolean
  teacher_note: string
}

export interface GroupActivity {
  id: string
  game_id: string
  title: string
  glyph: string
  tone: string
  group_name: string
  members: Member[]
  teammates: Member[]
  member_count: number
  instructions: string
}

/** What the screen needs before it can open a room: who you are playing with, and where. */
export interface ActivityMeta {
  title: string
  glyph: string
  groupName: string | null
  /** Every seat in the group, you included, so absent teammates still get a face. */
  members: Member[]
  teammates: Member[]
  memberCount: number
  instructions: string
  solo: boolean
}

export const SOLO = 'solo'

interface Resolved {
  meta: ActivityMeta | null
  roomId: string
  error: string
}

/** Resolve a route pair (gameId, activityId) into a room id the server will accept. */
export function useActivity(gameId: string, activityId: string): Resolved {
  const [resolved, setResolved] = useState<Resolved>({ meta: null, roomId: '', error: '' })

  useEffect(() => {
    let live = true
    if (!gameId || !activityId) {
      setResolved({ meta: null, roomId: '', error: 'This activity is not available.' })
      return
    }

    if (activityId === SOLO) {
      api<GameSpec[]>('/games')
        .then((catalog) => {
          if (!live) return
          const spec = catalog.find((game) => game.id === gameId)
          if (!spec || !spec.solo) {
            setResolved({ meta: null, roomId: '', error: 'This game cannot be played on your own.' })
            return
          }
          setResolved({
            meta: {
              title: spec.title, glyph: spec.glyph, groupName: null, members: [], teammates: [],
              memberCount: 1, instructions: spec.instructions, solo: true,
            },
            roomId: `solo:${gameId}`,
            error: '',
          })
        })
        .catch(() => { if (live) setResolved({ meta: null, roomId: '', error: 'The game could not load. Try again.' }) })
      return () => { live = false }
    }

    api<GroupActivity[]>('/student/group-activities')
      .then((activities) => {
        if (!live) return
        const assigned = activities.find((row) => row.id === activityId && row.game_id === gameId)
        if (!assigned) {
          setResolved({ meta: null, roomId: '', error: 'This activity is not assigned to your group.' })
          return
        }
        setResolved({
          meta: {
            title: assigned.title,
            glyph: assigned.glyph,
            groupName: assigned.group_name,
            members: assigned.members,
            teammates: assigned.teammates,
            memberCount: assigned.member_count,
            instructions: assigned.instructions,
            solo: false,
          },
          roomId: assigned.id,
          error: '',
        })
      })
      .catch(() => { if (live) setResolved({ meta: null, roomId: '', error: 'The activity could not load. Try again.' }) })

    return () => { live = false }
  }, [gameId, activityId])

  return resolved
}

export interface Room<S> {
  snapshot: RoomSnapshot<S> | null
  connection: Connection
  error: string
  send: (action: Record<string, unknown>) => void
  studentId: string
}

/** Open the shared room and keep the latest server snapshot. */
export function useActivityRoom<S>(roomId: string): Room<S> {
  const session = getSession()
  const studentId = session?.role === 'student' ? session.userId : ''
  const socket = useRef<WebSocket | null>(null)
  const [snapshot, setSnapshot] = useState<RoomSnapshot<S> | null>(null)
  const [connection, setConnection] = useState<Connection>('connecting')
  const [error, setError] = useState('')
  const opened = useRef(false)

  useEffect(() => {
    if (!roomId || !studentId) return
    let live = true
    opened.current = false
    const protocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:'
    // The socket is authorised by the same token the REST calls carry. A WebSocket
    // handshake cannot set headers, so it travels as a query parameter; the server reads
    // the learner's identity out of the token's claims rather than off the wire.
    const session = getSession()
    if (!session?.token) { setError('Sign in to join this activity.'); return }
    const params = new URLSearchParams({ token: session.token })
    const ws = new WebSocket(`${protocol}//${window.location.host}/api/games/ws/activity/${encodeURIComponent(roomId)}?${params}`)
    socket.current = ws

    ws.onmessage = (event) => {
      if (!live) return
      const message = JSON.parse(event.data) as RoomSnapshot<S> | { type: 'error'; message: string }
      if (message.type === 'error') { setError(message.message); return }
      opened.current = true
      setSnapshot(message)
      setConnection('live')
    }
    ws.onerror = () => { if (live) setError('The activity could not connect. Try opening it again.') }
    ws.onclose = (event) => { if (live && event.code !== 1000 && opened.current) setConnection('lost') }

    return () => {
      live = false
      ws.close(1000)
      if (socket.current === ws) socket.current = null
    }
  }, [roomId, studentId])

  function send(action: Record<string, unknown>) {
    if (socket.current?.readyState === WebSocket.OPEN) socket.current.send(JSON.stringify(action))
  }

  return { snapshot, connection, error, send, studentId }
}

/** The colour of whoever last touched a square, so a child can see their teammate working. */
export function editorColor(participants: Participant[], playerId: string | null | undefined) {
  if (!playerId) return undefined
  return participants.find((person) => person.id === playerId)?.color
}

export function editorName(participants: Participant[], playerId: string | null | undefined) {
  if (!playerId) return ''
  return participants.find((person) => person.id === playerId)?.name ?? ''
}
