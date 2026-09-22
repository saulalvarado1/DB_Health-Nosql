import type { Alert, MonitoredDatabase, MonitoringHistory } from '../api/contracts'
import { alertsApi, databasesApi } from '../api/resources'

export interface DatabaseSnapshot {
  database: MonitoredDatabase
  latest: MonitoringHistory | null
}

export interface DashboardSnapshot {
  databases: DatabaseSnapshot[]
  alerts: Alert[]
}

const HISTORY_CONCURRENCY = 4

async function loadLatestSamples(databases: MonitoredDatabase[]): Promise<DatabaseSnapshot[]> {
  const snapshots: DatabaseSnapshot[] = []

  for (let offset = 0; offset < databases.length; offset += HISTORY_CONCURRENCY) {
    const batch = databases.slice(offset, offset + HISTORY_CONCURRENCY)
    const batchSnapshots = await Promise.all(
      batch.map(async (database) => {
        try {
          const [latest] = await databasesApi.history(database.id, 1)
          return { database, latest: latest ?? null }
        } catch {
          return { database, latest: null }
        }
      }),
    )
    snapshots.push(...batchSnapshots)
  }

  return snapshots
}

export async function loadDashboard(): Promise<DashboardSnapshot> {
  const [databases, alerts] = await Promise.all([databasesApi.list(), alertsApi.list()])
  return {
    databases: await loadLatestSamples(databases),
    alerts,
  }
}
