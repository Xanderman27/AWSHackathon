// The Dori product mark: three smooth diagonal stripes (red, yellow, green), side by side.
// The product logo is this mark; Capy the mascot lives in the content, not the logo.

export function DoriLogo({ size = 40, className = '' }: { size?: number; className?: string }) {
  return (
    <svg viewBox="0 0 48 48" width={size} height={size} aria-hidden="true"
      className={className} style={{ display: 'block', overflow: 'visible' }}>
      <g transform="rotate(38 24 24)">
        <rect className="logo-stripe" x="8.2" y="7.5" width="8.8" height="33" rx="4.4" fill="#ff4b4b" />
        <rect className="logo-stripe" x="19.6" y="7.5" width="8.8" height="33" rx="4.4" fill="#ffc800" />
        <rect className="logo-stripe" x="31" y="7.5" width="8.8" height="33" rx="4.4" fill="#58cc02" />
      </g>
    </svg>
  )
}
