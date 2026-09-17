// A learner's face. A photo when there is one, and an illustrated face drawn in the same
// hand-drawn style as the path badges when there is not (or when the photo fails to load).
//
// The photos are stock portraits of real children; see public/faces/CREDITS.md for what that
// means before this is shown outside an internal demo.

import { useState } from 'react'

export type HairStyle =
  | 'short' | 'buzz' | 'curly' | 'coily' | 'long' | 'bob' | 'ponytail' | 'bun' | 'braids' | 'wavy'
  | 'puffs'

export interface AvatarSpec {
  skin: number
  hair: HairStyle
  hair_color: number
  shirt: number
  glasses?: boolean
  freckles?: boolean
}

const SKIN = [
  { fill: '#fbdcc4', line: '#d9a17a' },
  { fill: '#f2c49b', line: '#c98f63' },
  { fill: '#dda172', line: '#ad7245' },
  { fill: '#b97a4e', line: '#8a5430' },
  { fill: '#8d5a34', line: '#653c20' },
  { fill: '#5f3a1e', line: '#3f2513' },
]

const HAIR = [
  { fill: '#2b2118', line: '#140e09' },
  { fill: '#4a2f1b', line: '#2c1a0d' },
  { fill: '#8a5a2b', line: '#5f3c19' },
  { fill: '#c98f3a', line: '#96651f' },
  { fill: '#e8c06a', line: '#b48f3c' },
  { fill: '#b5462f', line: '#83301e' },
  { fill: '#6b6f76', line: '#464a50' },
]

const SHIRT = ['#2869dd', '#2e8b57', '#c84b7a', '#9b5de5', '#e08b2f', '#1c9aa8']

const pick = <T,>(list: T[], index: number) => list[((index % list.length) + list.length) % list.length]

interface Props {
  photo?: string | null
  spec?: AvatarSpec | null
  size?: number
  /** Announce the face as this person. Omit to leave it decorative beside a visible name. */
  name?: string
  className?: string
}

/** A learner's face: the photo when one loads, the drawn face otherwise. */
export default function Avatar({ photo, spec, size = 44, name, className = '' }: Props) {
  const [broken, setBroken] = useState(false)
  const label = name ? { alt: name } : { alt: '', 'aria-hidden': true as const }

  if (photo && !broken) {
    return (
      <img
        className={`face photo ${className}`} src={photo} width={size} height={size}
        loading="lazy" decoding="async" onError={() => setBroken(true)} {...label}
      />
    )
  }
  return <DrawnFace spec={spec} size={size} name={name} className={className} />
}

function DrawnFace({ spec, size = 44, name, className = '' }: Omit<Props, 'photo'>) {
  const s = spec ?? FALLBACK
  const skin = pick(SKIN, s.skin)
  const hair = pick(HAIR, s.hair_color)
  const shirt = pick(SHIRT, s.shirt)
  const tag = name ? { role: 'img', 'aria-label': name } : { 'aria-hidden': true as const }

  return (
    <svg className={`face ${className}`} width={size} height={size} viewBox="0 0 100 100" {...tag}>
      {/* shoulders, so the face sits on a person rather than floating */}
      <path d="M12 100 C12 80 30 72 50 72 C70 72 88 80 88 100 Z" fill={shirt} />
      <rect x="43" y="60" width="14" height="16" rx="7" fill={skin.fill} />

      {backHair(s.hair, hair)}

      <circle cx="24" cy="50" r="5.5" fill={skin.fill} stroke={skin.line} strokeWidth="1.5" />
      <circle cx="76" cy="50" r="5.5" fill={skin.fill} stroke={skin.line} strokeWidth="1.5" />
      <ellipse cx="50" cy="47" rx="25" ry="27" fill={skin.fill} stroke={skin.line} strokeWidth="2" />

      {frontHair(s.hair, hair)}

      {s.freckles && (
        <g fill={skin.line} opacity="0.75">
          <circle cx="35" cy="53" r="1.1" /><circle cx="39" cy="55.5" r="1.1" /><circle cx="31.5" cy="56" r="1.1" />
          <circle cx="65" cy="53" r="1.1" /><circle cx="61" cy="55.5" r="1.1" /><circle cx="68.5" cy="56" r="1.1" />
        </g>
      )}

      <ellipse cx="33" cy="57" rx="4.6" ry="3" fill="#e8737e" opacity="0.32" />
      <ellipse cx="67" cy="57" rx="4.6" ry="3" fill="#e8737e" opacity="0.32" />

      <circle cx="41" cy="47" r="3.5" fill="#241a12" />
      <circle cx="59" cy="47" r="3.5" fill="#241a12" />
      <circle cx="42.2" cy="45.7" r="1.2" fill="#fff" />
      <circle cx="60.2" cy="45.7" r="1.2" fill="#fff" />

      {s.glasses && (
        <g fill="none" stroke="#3b3b44" strokeWidth="2.2">
          <circle cx="41" cy="47" r="8" /><circle cx="59" cy="47" r="8" />
          <path d="M49 47 h2 M33 46 l-6 -2 M67 46 l6 -2" strokeLinecap="round" />
        </g>
      )}

      <path d="M42 58 q8 7 16 0" fill="none" stroke="#7a4030" strokeWidth="2.4" strokeLinecap="round" />
    </svg>
  )
}

const FALLBACK: AvatarSpec = { skin: 1, hair: 'short', hair_color: 1, shirt: 0 }

/** Hair drawn behind the head: anything that falls past the jaw. */
function backHair(style: HairStyle, hair: { fill: string; line: string }) {
  const stroke = { stroke: hair.line, strokeWidth: 2, strokeLinejoin: 'round' as const }
  switch (style) {
    case 'long':
      return <path d="M20 46 C20 22 34 14 50 14 C66 14 80 22 80 46 L80 84 L68 78 L68 48 L32 48 L32 78 L20 84 Z" fill={hair.fill} {...stroke} />
    case 'bob':
      return <path d="M21 46 C21 22 34 14 50 14 C66 14 79 22 79 46 L79 64 L66 60 L66 46 L34 46 L34 60 L21 64 Z" fill={hair.fill} {...stroke} />
    case 'wavy':
      return <path d="M20 46 C20 22 34 14 50 14 C66 14 80 22 80 46 C80 58 84 62 80 70 C76 62 74 58 74 48 L26 48 C26 58 24 62 20 70 C16 62 20 58 20 46 Z" fill={hair.fill} {...stroke} />
    case 'braids':
      return (
        <g fill={hair.fill} {...stroke}>
          <rect x="16" y="42" width="12" height="34" rx="6" />
          <rect x="72" y="42" width="12" height="34" rx="6" />
        </g>
      )
    case 'ponytail':
      return <path d="M76 36 C90 40 92 58 84 70 C80 60 74 52 70 46 Z" fill={hair.fill} {...stroke} />
    case 'puffs':
      return (
        <g fill={hair.fill} {...stroke}>
          <circle cx="14" cy="34" r="13" />
          <circle cx="86" cy="34" r="13" />
        </g>
      )
    default:
      return null
  }
}

/** Hair drawn over the head: the part that covers the forehead. */
function frontHair(style: HairStyle, hair: { fill: string; line: string }) {
  const stroke = { stroke: hair.line, strokeWidth: 2, strokeLinejoin: 'round' as const }
  const cap = <path d="M25 44 C25 22 36 15 50 15 C64 15 75 22 75 44 C71 33 62 28 50 28 C38 28 29 33 25 44 Z" fill={hair.fill} {...stroke} />

  switch (style) {
    case 'buzz':
      return <path d="M26 42 C26 24 37 18 50 18 C63 18 74 24 74 42 C70 34 62 31 50 31 C38 31 30 34 26 42 Z" fill={hair.fill} {...stroke} />
    case 'curly':
    case 'coily': {
      const tight = style === 'coily'
      const r = tight ? 9 : 8
      const puffs: Array<[number, number]> = tight
        ? [[28, 34], [38, 25], [50, 21], [62, 25], [72, 34], [25, 45], [75, 45]]
        : [[30, 33], [40, 26], [50, 23], [60, 26], [70, 33]]
      return (
        <g fill={hair.fill} {...stroke}>
          {puffs.map(([cx, cy], i) => <circle key={i} cx={cx} cy={cy} r={r} />)}
        </g>
      )
    }
    case 'puffs': {
      const puffs: Array<[number, number]> = [[30, 33], [40, 25], [50, 22], [60, 25], [70, 33]]
      return (
        <g fill={hair.fill} {...stroke}>
          {puffs.map(([cx, cy], i) => <circle key={i} cx={cx} cy={cy} r={9} />)}
        </g>
      )
    }
    case 'bun':
      return (
        <g fill={hair.fill} {...stroke}>
          <circle cx="50" cy="13" r="10" />
          {cap.props.d && <path d={cap.props.d} fill={hair.fill} {...stroke} />}
        </g>
      )
    case 'ponytail':
    case 'braids':
    case 'long':
    case 'bob':
    case 'wavy':
    case 'short':
    default:
      return cap
  }
}
