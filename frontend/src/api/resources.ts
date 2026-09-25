import type {
  AccessTokenResponse,
  Alert,
  AlertStatus,
  AuthCredentials,
  CreateMonitoredDatabase,
  HistoryTimeRange,
  MonitoredDatabase,
  MonitoringHistory,
  MonitoringRun,
  ThresholdProfile,
  UpdateMonitoredDatabase,
  User,
} from './contracts'
import { httpClient } from './http-client'

const segment = (value: string) => encodeURIComponent(value)

export const authApi = {
  register: (credentials: AuthCredentials) => httpClient.post<User>('/auth/register', credentials),
  login: (credentials: AuthCredentials) =>
    httpClient.post<AccessTokenResponse>('/auth/login', credentials),
  me: () => httpClient.get<User>('/auth/me'),
}

export const databasesApi = {
  list: () => httpClient.get<MonitoredDatabase[]>('/databases'),
  get: (databaseId: string) =>
    httpClient.get<MonitoredDatabase>(`/databases/${segment(databaseId)}`),
  create: (payload: CreateMonitoredDatabase) =>
    httpClient.post<MonitoredDatabase>('/databases', payload),
  update: (databaseId: string, payload: UpdateMonitoredDatabase) =>
    httpClient.patch<MonitoredDatabase>(`/databases/${segment(databaseId)}`, payload),
  remove: (databaseId: string) => httpClient.delete(`/databases/${segment(databaseId)}`),
  history: (databaseId: string, limit = 100, range?: HistoryTimeRange) => {
    const rangeParam = range && range !== 'all' ? `&range=${encodeURIComponent(range)}` : ''
    return httpClient.get<MonitoringHistory[]>(
      `/databases/${segment(databaseId)}/history?limit=${Math.min(Math.max(limit, 1), 1000)}${rangeParam}`,
    )
  },
  collect: (databaseId: string) =>
    httpClient.post<MonitoringRun>(`/databases/${segment(databaseId)}/collect`),
  thresholds: (databaseId: string) =>
    httpClient.get<ThresholdProfile>(`/databases/${segment(databaseId)}/thresholds`),
  updateThreshold: (
    databaseId: string,
    metricCode: string,
    payload: { warning_value: number; critical_value: number },
  ) =>
    httpClient.put<ThresholdProfile>(
      `/databases/${segment(databaseId)}/thresholds/${segment(metricCode)}`,
      payload,
    ),
  exportReport: (
    databaseId: string,
    format: 'csv' | 'json' = 'csv',
    limit = 100,
    range?: HistoryTimeRange,
  ) => {
    const rangeParam = range && range !== 'all' ? `&range=${encodeURIComponent(range)}` : ''
    return httpClient.download(
      `/databases/${segment(databaseId)}/export?format=${format}&limit=${limit}${rangeParam}`,
      `reporte_salud_${databaseId}.${format}`,
    )
  },
}

export const alertsApi = {
  list: (status?: AlertStatus) =>
    httpClient.get<Alert[]>(`/alerts${status ? `?status=${segment(status)}` : ''}`),
  acknowledge: (alertId: string) =>
    httpClient.post<Alert>(`/alerts/${segment(alertId)}/acknowledge`),
}
