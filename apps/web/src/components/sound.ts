// A tiny synthesized "hurray!" for right answers. Web Audio only - no sound files to load,
// and it fails silently anywhere audio is blocked (the answer feedback never depends on it).

let ctx: AudioContext | null = null

export function playHurray() {
  try {
    ctx = ctx ?? new AudioContext()
    if (ctx.state === 'suspended') void ctx.resume()
    const start = ctx.currentTime
    // A quick, bright C-major fanfare: C5 E5 G5, then a longer C6 on top.
    const notes: [number, number, number][] = [
      [523.25, 0, 0.22], [659.25, 0.09, 0.22], [783.99, 0.18, 0.22], [1046.5, 0.27, 0.45],
    ]
    for (const [freq, at, length] of notes) {
      const osc = ctx.createOscillator()
      const gain = ctx.createGain()
      osc.type = 'triangle'
      osc.frequency.value = freq
      const t = start + at
      gain.gain.setValueAtTime(0.0001, t)
      gain.gain.exponentialRampToValueAtTime(0.16, t + 0.02)
      gain.gain.exponentialRampToValueAtTime(0.0001, t + length)
      osc.connect(gain).connect(ctx.destination)
      osc.start(t)
      osc.stop(t + length + 0.05)
    }
  } catch {
    /* no audio available; stay quiet */
  }
}
