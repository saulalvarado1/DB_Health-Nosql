export type DatabaseEngine = 'mongodb' | 'redis'
export type HealthStatus = 'healthy' | 'warning' | 'critical' | 'unknown'
export type MetricDiagnosticStatus = 'healthy' | 'warning' | 'critical' | 'informational'
export type MetricDiagnosticBasis = 'threshold' | 'heuristic' | 'informational'
export type AlertSeverity = 'warning' | 'critical'
export type AlertStatus = 'open' | 'acknowledged' | 'resolved'
export type HistoryTimeRange = '1h' | '6h' | '24h' | '7d' | 'all'

export interface User {
  id: string
  email: string
  is_active: boolean
  created_at: string
}

export interface AccessTokenResponse {
  access_token: string
  token_type: 'bearer'
}

export interface AuthCredentials {
  email: string
  password: string
}

export interface MonitoredDatabase {
  id: string
  name: string
  engine: DatabaseEngine
  interval_seconds: number
  is_enabled: boolean
  created_at: string
}

export interface CreateMonitoredDatabase {
  name: string
  engine: DatabaseEngine
  connection_uri: string
  interval_seconds: number
}

export interface UpdateMonitoredDatabase {
  name?: string
  interval_seconds?: number
  is_enabled?: boolean
}

export interface MetricValue {
  code: string
  display_name: string
  unit: string
  value: number
  status: MetricDiagnosticStatus
  diagnostic_basis: MetricDiagnosticBasis
  message: string
}

export interface MonitoringHistory {
  sample_id: string
  collected_at: string
  collection_succeeded: boolean
  error_message: string | null
  health_score: number
  health_status: HealthStatus
  evaluated_at: string
  metrics: MetricValue[]
}

export interface MonitoringRun {
  sample_id: string
  collected_at: string
  collection_succeeded: boolean
  health_score: number
  health_status: HealthStatus
  metric_count: number
}

export interface ThresholdRule {
  metric_definition_id: string
  metric_code: string
  display_name: string
  unit: string
  alert_direction: 'above' | 'below'
  warning_value: number
  critical_value: number
}

export interface ThresholdProfile {
  id: string
  name: string
  engine: DatabaseEngine
  is_default: boolean
  rules: ThresholdRule[]
}

export interface Alert {
  id: string
  monitored_database_id: string
  sample_id: string | null
  threshold_rule_id: string | null
  severity: AlertSeverity
  status: AlertStatus
  message: string
  resolved_at: string | null
  created_at: string
  updated_at: string
}
