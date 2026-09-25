db.getSiblingDB('admin').createUser({
  user: 'monitor',
  pwd: 'MonitorPass123!',
  roles: [
    { role: 'clusterMonitor', db: 'admin' }
  ]
});
