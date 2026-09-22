import { useMemo, useState } from 'react'

import type { MetricDiagnosticStatus, MetricValue } from '../api/contracts'
import { diagnosticBasisLabels, formatMetric } from '../core/format'
import { StatusBadge } from './ui'

type MetricGroupId = 'attention' | 'healthy' | 'informational'

interface MetricGroupDefinition {
  id: MetricGroupId
  title: string
  description: string
  statuses: MetricDiagnosticStatus[]
}

const metricGroups: MetricGroupDefinition[] = [
  {
    id: 'attention',
    title: 'Requieren atención',
    description: 'Condiciones críticas o de advertencia que conviene revisar primero.',
    statuses: ['critical', 'warning'],
  },
  {
    id: 'healthy',
    title: 'Estado verificado',
    description: 'Comprobaciones que cumplen su umbral o condición operativa.',
    statuses: ['healthy'],
  },
  {
    id: 'informational',
    title: 'Datos informativos',
    description: 'Indicadores que necesitan contexto o una línea base propia.',
    statuses: ['informational'],
  },
]

const summaryOrder: Array<{
  status: MetricDiagnosticStatus
  label: string
}> = [
  { status: 'critical', label: 'Críticas' },
  { status: 'warning', label: 'Advertencias' },
  { status: 'healthy', label: 'Saludables' },
  { status: 'informational', label: 'Informativas' },
]

function MetricRow({ metric }: { metric: MetricValue }) {
  return (
    <article className={`metric-row metric-row--${metric.status}`}>
      <div className="metric-row__identity">
        <strong>{metric.display_name}</strong>
        <small className="mono">{metric.code}</small>
      </div>
      <strong className="metric-row__value">{formatMetric(metric.value, metric.unit)}</strong>
      <StatusBadge status={metric.status} />
      <div className="metric-row__diagnostic">
        <p>{metric.message}</p>
        <small>{diagnosticBasisLabels[metric.diagnostic_basis]}</small>
      </div>
    </article>
  )
}

export function MetricCatalog({ metrics }: { metrics: MetricValue[] }) {
  const groupedMetrics = useMemo(
    () => metricGroups.map((group) => ({
      ...group,
      metrics: metrics.filter((metric) => group.statuses.includes(metric.status)),
    })),
    [metrics],
  )
  const counts = useMemo(
    () => Object.fromEntries(
      summaryOrder.map(({ status }) => [
        status,
        metrics.filter((metric) => metric.status === status).length,
      ]),
    ) as Record<MetricDiagnosticStatus, number>,
    [metrics],
  )
  const [expanded, setExpanded] = useState<Record<MetricGroupId, boolean>>({
    attention: true,
    healthy: false,
    informational: false,
  })

  function toggleGroup(groupId: MetricGroupId) {
    setExpanded((current) => ({ ...current, [groupId]: !current[groupId] }))
  }

  return (
    <>
      <div className="metric-summary" aria-label="Resumen de diagnósticos">
        {summaryOrder.map(({ status, label }) => (
          <div className={`metric-summary__item metric-summary__item--${status}`} key={status}>
            <strong>{counts[status]}</strong>
            <span>{label}</span>
          </div>
        ))}
      </div>

      <div className="metric-groups">
        {groupedMetrics
          .filter((group) => group.metrics.length > 0)
          .map((group) => (
            <section className={`metric-group metric-group--${group.id}`} key={group.id}>
              <button
                className="metric-group__toggle"
                type="button"
                aria-expanded={expanded[group.id]}
                aria-controls={`metric-group-${group.id}`}
                onClick={() => toggleGroup(group.id)}
              >
                <span>
                  <strong>{group.title}</strong>
                  <small>{group.description}</small>
                </span>
                <span className="metric-group__count">
                  {group.metrics.length} {group.metrics.length === 1 ? 'métrica' : 'métricas'}
                  <span aria-hidden="true">{expanded[group.id] ? '−' : '+'}</span>
                </span>
              </button>

              {expanded[group.id] && (
                <div className="metric-rows" id={`metric-group-${group.id}`}>
                  {group.metrics.map((metric) => <MetricRow key={metric.code} metric={metric} />)}
                </div>
              )}
            </section>
          ))}
      </div>
    </>
  )
}
