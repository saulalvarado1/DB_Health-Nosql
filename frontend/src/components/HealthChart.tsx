import type { MonitoringHistory } from '../api/contracts'

const WIDTH = 720
const HEIGHT = 180
const PADDING = 18

export function HealthChart({ history }: { history: MonitoringHistory[] }) {
  const samples = [...history].reverse()
  if (samples.length < 2) {
    return <p className="muted">Se necesitan al menos dos muestras para dibujar la tendencia.</p>
  }

  const usableWidth = WIDTH - PADDING * 2
  const usableHeight = HEIGHT - PADDING * 2
  const denominator = Math.max(samples.length - 1, 1)
  const points = samples
    .map((sample, index) => {
      const x = PADDING + (index / denominator) * usableWidth
      const y = PADDING + ((100 - sample.health_score) / 100) * usableHeight
      return `${x},${y}`
    })
    .join(' ')

  return (
    <div className="chart" role="img" aria-label="Evolución del puntaje de salud">
      <svg viewBox={`0 0 ${WIDTH} ${HEIGHT}`} preserveAspectRatio="none">
        <line x1={PADDING} y1={PADDING} x2={WIDTH - PADDING} y2={PADDING} />
        <line x1={PADDING} y1={HEIGHT / 2} x2={WIDTH - PADDING} y2={HEIGHT / 2} />
        <line x1={PADDING} y1={HEIGHT - PADDING} x2={WIDTH - PADDING} y2={HEIGHT - PADDING} />
        <polyline points={points} />
      </svg>
      <div className="chart__labels" aria-hidden="true"><span>100</span><span>50</span><span>0</span></div>
    </div>
  )
}
