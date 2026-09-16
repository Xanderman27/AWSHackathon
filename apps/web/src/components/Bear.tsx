// Dori, the friendly bear. Drawn as SVG so it renders identically everywhere and can be
// outlined for high-contrast mode (emoji cannot be restyled).

type Mood = 'happy' | 'wave' | 'think' | 'cheer'

export default function Bear({ mood = 'happy', size = 72, float = false, className = '' }:
  { mood?: Mood; size?: number; float?: boolean; className?: string }) {
  const eyeY = mood === 'cheer' ? 40 : 42
  return (
    <svg
      className={`bear ${float ? 'floaty' : ''} ${className}`}
      width={size} height={size} viewBox="0 0 100 100" role="img" aria-label="Dori the bear"
    >
      {/* ears */}
      <circle cx="24" cy="24" r="13" className="bear-fur" />
      <circle cx="76" cy="24" r="13" className="bear-fur" />
      <circle cx="24" cy="24" r="6" className="bear-inner" />
      <circle cx="76" cy="24" r="6" className="bear-inner" />
      {/* head */}
      <circle cx="50" cy="52" r="34" className="bear-fur" />
      {/* muzzle */}
      <ellipse cx="50" cy="63" rx="19" ry="15" className="bear-inner" />
      {/* eyes */}
      {mood === 'cheer' ? (
        <>
          <path d="M34 42 q5 -6 10 0" className="bear-line" fill="none" />
          <path d="M56 42 q5 -6 10 0" className="bear-line" fill="none" />
        </>
      ) : (
        <>
          <circle cx="39" cy={eyeY} r="4.2" className="bear-eye" />
          <circle cx="61" cy={eyeY} r="4.2" className="bear-eye" />
          <circle cx="40.3" cy={eyeY - 1.4} r="1.4" fill="#fff" />
          <circle cx="62.3" cy={eyeY - 1.4} r="1.4" fill="#fff" />
        </>
      )}
      {/* nose + mouth */}
      <ellipse cx="50" cy="57" rx="5.5" ry="4" className="bear-eye" />
      <path d="M50 61 v4" className="bear-line" fill="none" />
      {mood === 'think'
        ? <path d="M43 69 q7 -3 14 0" className="bear-line" fill="none" />
        : <path d="M42 66 q8 8 16 0" className="bear-line" fill="none" />}
      {/* blush */}
      <ellipse cx="26" cy="58" rx="5" ry="3.4" className="bear-blush" />
      <ellipse cx="74" cy="58" rx="5" ry="3.4" className="bear-blush" />
      {mood === 'wave' && <circle cx="88" cy="74" r="9" className="bear-fur bear-paw" />}
    </svg>
  )
}
