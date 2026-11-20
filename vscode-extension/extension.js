const vscode = require('vscode');
const https = require('https');
const http = require('http');

/**
 * Petición HTTP/HTTPS promisificada nativa (sin dependencias externas)
 */
function apiRequest(urlStr, method = 'GET', data = null, token = null) {
  return new Promise((resolve, reject) => {
    try {
      const parsedUrl = new URL(urlStr);
      const isHttps = parsedUrl.protocol === 'https:';
      const client = isHttps ? https : http;

      const headers = {
        'User-Agent': 'VSCode-DBHealthMonitor/1.1',
        Accept: 'application/json'
      };

      let bodyData = null;
      if (data) {
        bodyData = JSON.stringify(data);
        headers['Content-Type'] = 'application/json';
        headers['Content-Length'] = Buffer.byteLength(bodyData);
      }

      if (token) {
        headers['Authorization'] = `Bearer ${token.trim()}`;
      }

      const options = {
        hostname: parsedUrl.hostname,
        port: parsedUrl.port || (isHttps ? 443 : 80),
        path: parsedUrl.pathname + parsedUrl.search,
        method,
        headers,
        timeout: 6000
      };

      const req = client.request(options, (res) => {
        let responseBody = '';
        res.on('data', (chunk) => (responseBody += chunk));
        res.on('end', () => {
          let parsed = null;
          try {
            parsed = responseBody ? JSON.parse(responseBody) : null;
          } catch {
            parsed = responseBody;
          }

          if (res.statusCode >= 200 && res.statusCode < 300) {
            resolve(parsed);
          } else {
            const error = new Error((parsed && parsed.detail) || `HTTP Error ${res.statusCode}`);
            error.statusCode = res.statusCode;
            reject(error);
          }
        });
      });

      req.on('timeout', () => {
        req.destroy();
        reject(new Error('Tiempo de espera agotado al conectar con DB Health Monitor'));
      });

      req.on('error', (err) => reject(err));

      if (bodyData) {
        req.write(bodyData);
      }
      req.end();
    } catch (err) {
      reject(err);
    }
  });
}

/**
 * Árbol de elementos para la barra lateral de VS Code
 */
class DatabaseTreeItem extends vscode.TreeItem {
  constructor(label, collapsibleState, data = null, command = null) {
    super(label, collapsibleState);
    this.data = data;
    if (command) {
      this.command = command;
    }
  }
}

class DBHealthTreeDataProvider {
  constructor(context) {
    this.context = context;
    this._onDidChangeTreeData = new vscode.EventEmitter();
    this.onDidChangeTreeData = this._onDidChangeTreeData.event;
    this.databases = [];
    this.hasActiveSession = false;
  }

  refresh() {
    this._onDidChangeTreeData.fire();
  }

  getTreeItem(element) {
    return element;
  }

  async getToken() {
    // Primero revisa el almacenamiento seguro de secretos, luego la configuración
    let token = await this.context.secrets.get('dbhealth_token');
    if (!token) {
      const config = vscode.workspace.getConfiguration('dbhealth');
      token = (config.get('apiToken') || '').trim();
    }
    return token ? token.trim() : null;
  }

  async setToken(token) {
    if (token) {
      await this.context.secrets.store('dbhealth_token', token.trim());
    } else {
      await this.context.secrets.delete('dbhealth_token');
    }
    this.refresh();
  }

  getBaseUrl() {
    const config = vscode.workspace.getConfiguration('dbhealth');
    return (config.get('apiUrl') || 'https://dbhealth.alvarado1.tech').replace(/\/+$/, '');
  }

  async getChildren(element) {
    const token = await this.getToken();
    const apiUrl = this.getBaseUrl();

    // 1. Nivel Raíz (Si no hay token guardado)
    if (!element) {
      if (!token) {
        this.hasActiveSession = false;
        return [
          new DatabaseTreeItem(
            '🔑 Conectar con Token de Acceso (Web/Google)',
            vscode.TreeItemCollapsibleState.None,
            null,
            { command: 'dbhealth.setToken', title: 'Conectar Token' }
          ),
          new DatabaseTreeItem(
            '✉️ Iniciar Sesión con Correo y Contraseña',
            vscode.TreeItemCollapsibleState.None,
            null,
            { command: 'dbhealth.login', title: 'Iniciar Sesión' }
          ),
          new DatabaseTreeItem(
            '🌐 Abrir Plataforma Web (alvarado1.tech)',
            vscode.TreeItemCollapsibleState.None,
            null,
            { command: 'dbhealth.openDashboard', title: 'Abrir Web' }
          )
        ];
      }

      // Si hay token: Consultar bases de datos reales del usuario
      try {
        const dbs = await apiRequest(`${apiUrl}/api/v1/databases`, 'GET', null, token);
        this.hasActiveSession = true;
        this.databases = Array.isArray(dbs) ? dbs : [];

        if (this.databases.length === 0) {
          return [
            new DatabaseTreeItem(
              'ℹ️ Aún no tienes bases de datos registradas',
              vscode.TreeItemCollapsibleState.None
            ),
            new DatabaseTreeItem(
              '➕ Registrar nueva base de datos en la web',
              vscode.TreeItemCollapsibleState.None,
              null,
              { command: 'dbhealth.createDatabase', title: 'Nueva Base de Datos' }
            ),
            new DatabaseTreeItem(
              '🚪 Cerrar Sesión',
              vscode.TreeItemCollapsibleState.None,
              null,
              { command: 'dbhealth.logout', title: 'Cerrar Sesión' }
            )
          ];
        }

        // Consultar telemetría de cada base de datos en paralelo
        const items = await Promise.all(
          this.databases.map(async (db) => {
            let score = 100;
            let status = 'healthy';
            let metrics = [];

            try {
              const history = await apiRequest(
                `${apiUrl}/api/v1/databases/${db.id}/history?range=1h`,
                'GET',
                null,
                token
              );
              if (Array.isArray(history) && history.length > 0) {
                const latest = history[0];
                score = latest.health_score ?? 100;
                status = latest.health_status ?? 'healthy';
                metrics = latest.metrics || [];
              }
            } catch {
              // Si no tiene historial aún, se muestra como activa
              status = db.is_enabled ? 'healthy' : 'unknown';
            }

            const statusIcon = status === 'critical' ? '🔴' : status === 'warning' ? '🟡' : '🟢';
            const engineIcon = db.engine === 'mongodb' ? '🍃' : '⚡';

            const treeItem = new DatabaseTreeItem(
              `${engineIcon} ${db.name} (${statusIcon} ${score}/100)`,
              vscode.TreeItemCollapsibleState.Collapsed,
              { ...db, score, status, metrics }
            );
            treeItem.description = `${db.engine.toUpperCase()} • cada ${db.interval_seconds}s`;
            treeItem.tooltip = `Instancia: ${db.name} | Motor: ${db.engine} | Score: ${score}/100`;
            return treeItem;
          })
        );

        return items;
      } catch (err) {
        if (err.statusCode === 401) {
          this.hasActiveSession = false;
          return [
            new DatabaseTreeItem(
              '⚠️ Sesión expirada o token inválido',
              vscode.TreeItemCollapsibleState.None
            ),
            new DatabaseTreeItem(
              '🔑 Volver a conectar token de acceso',
              vscode.TreeItemCollapsibleState.None,
              null,
              { command: 'dbhealth.setToken', title: 'Reconectar Token' }
            )
          ];
        }

        return [
          new DatabaseTreeItem(
            `❌ Error al conectar con ${apiUrl}`,
            vscode.TreeItemCollapsibleState.None
          ),
          new DatabaseTreeItem(
            '🔄 Intentar de nuevo',
            vscode.TreeItemCollapsibleState.None,
            null,
            { command: 'dbhealth.refresh', title: 'Refrescar' }
          )
        ];
      }
    }

    // 2. Nivel Hijo: Métricas en vivo de la base de datos seleccionada
    const db = element.data;
    if (!db) return [];

    const children = [
      new DatabaseTreeItem(`📊 Health Score: ${db.score}/100 (${db.status.toUpperCase()})`, vscode.TreeItemCollapsibleState.None),
      new DatabaseTreeItem(`⏱️ Muestreo: cada ${db.interval_seconds} segundos`, vscode.TreeItemCollapsibleState.None)
    ];

    if (Array.isArray(db.metrics) && db.metrics.length > 0) {
      db.metrics.forEach((m) => {
        const mark = m.status === 'critical' ? '🔴' : m.status === 'warning' ? '🟡' : '🟢';
        children.push(
          new DatabaseTreeItem(
            `${mark} ${m.display_name}: ${m.value} ${m.unit}`,
            vscode.TreeItemCollapsibleState.None
          )
        );
      });
    } else {
      children.push(
        new DatabaseTreeItem('ℹ️ Esperando primera muestra de telemetría…', vscode.TreeItemCollapsibleState.None)
      );
    }

    children.push(
      new DatabaseTreeItem(
        '🌐 Ver gráficos e historial en la web',
        vscode.TreeItemCollapsibleState.None,
        null,
        {
          command: 'dbhealth.openDatabaseDetail',
          title: 'Ver en la Web',
          arguments: [db.id]
        }
      )
    );

    return children;
  }
}

/**
 * Activación de la extensión
 * @param {vscode.ExtensionContext} context
 */
function activate(context) {
  const treeDataProvider = new DBHealthTreeDataProvider(context);
  vscode.window.registerTreeDataProvider('dbhealth.databasesView', treeDataProvider);

  // Barra de estado inferior
  const statusBarItem = vscode.window.createStatusBarItem(vscode.StatusBarAlignment.Right, 100);
  statusBarItem.command = 'dbhealth.quickStatus';
  statusBarItem.show();
  context.subscriptions.push(statusBarItem);

  async function updateStatusBar() {
    const token = await treeDataProvider.getToken();
    if (!token) {
      statusBarItem.text = '$(key) DB Health: Conectar Cuenta';
      statusBarItem.tooltip = 'Haz clic para conectar tu cuenta de DB Health Monitor.';
    } else {
      const count = treeDataProvider.databases.length;
      statusBarItem.text = `$(database) DB Health: ${count} BD Monitoreadas`;
      statusBarItem.tooltip = `DB Health Monitor: Conectado a ${treeDataProvider.getBaseUrl()} (${count} instancias activas).`;
    }
  }

  updateStatusBar();

  // Comando: Refrescar
  const refreshCommand = vscode.commands.registerCommand('dbhealth.refresh', async () => {
    treeDataProvider.refresh();
    await updateStatusBar();
    vscode.window.showInformationMessage('DB Health Monitor: Estado de bases de datos actualizado.');
  });

  // Comando: Iniciar sesión con correo y contraseña
  const loginCommand = vscode.commands.registerCommand('dbhealth.login', async () => {
    const email = await vscode.window.showInputBox({
      title: 'Iniciar Sesión en DB Health Monitor',
      prompt: 'Ingresa tu correo electrónico registrado',
      placeHolder: 'usuario@ejemplo.com'
    });
    if (!email) return;

    const password = await vscode.window.showInputBox({
      title: 'Iniciar Sesión en DB Health Monitor',
      prompt: 'Ingresa tu contraseña',
      password: true
    });
    if (!password) return;

    try {
      vscode.window.showInformationMessage('Autenticando con DB Health Monitor…');
      const apiUrl = treeDataProvider.getBaseUrl();
      const res = await apiRequest(`${apiUrl}/api/v1/auth/login`, 'POST', {
        email: email.trim(),
        password
      });

      if (res && res.access_token) {
        await treeDataProvider.setToken(res.access_token);
        await updateStatusBar();
        vscode.window.showInformationMessage(`¡Bienvenido! Sesión iniciada como ${email}.`);
      }
    } catch (err) {
      vscode.window.showErrorMessage(`Error al iniciar sesión: ${err.message}`);
    }
  });

  // Comando: Ingresar token JWT directo (para usuarios de Google OAuth o Web)
  const setTokenCommand = vscode.commands.registerCommand('dbhealth.setToken', async () => {
    const token = await vscode.window.showInputBox({
      title: 'Conectar Token de Acceso de DB Health Monitor',
      prompt: 'Pega tu Token JWT (puedes copiarlo desde tu perfil en https://dbhealth.alvarado1.tech)',
      placeHolder: 'eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...',
      ignoreFocusOut: true
    });

    if (token !== undefined) {
      await treeDataProvider.setToken(token.trim());
      await updateStatusBar();
      if (token.trim()) {
        vscode.window.showInformationMessage('¡Token de acceso conectado correctamente!');
      } else {
        vscode.window.showInformationMessage('Sesión cerrada.');
      }
    }
  });

  // Comando: Cerrar sesión
  const logoutCommand = vscode.commands.registerCommand('dbhealth.logout', async () => {
    await treeDataProvider.setToken(null);
    await updateStatusBar();
    vscode.window.showInformationMessage('DB Health Monitor: Sesión cerrada.');
  });

  // Comando: Abrir Dashboard Web
  const openDashboardCommand = vscode.commands.registerCommand('dbhealth.openDashboard', () => {
    vscode.env.openExternal(vscode.Uri.parse(treeDataProvider.getBaseUrl()));
  });

  // Comando: Abrir formulario de nueva base de datos en la web
  const createDatabaseCommand = vscode.commands.registerCommand('dbhealth.createDatabase', () => {
    vscode.env.openExternal(vscode.Uri.parse(`${treeDataProvider.getBaseUrl()}/databases/new`));
  });

  // Comando: Abrir detalle de una base de datos específica
  const openDatabaseDetailCommand = vscode.commands.registerCommand('dbhealth.openDatabaseDetail', (dbId) => {
    vscode.env.openExternal(vscode.Uri.parse(`${treeDataProvider.getBaseUrl()}/databases/${dbId}`));
  });

  // Comando: QuickStatus
  const quickStatusCommand = vscode.commands.registerCommand('dbhealth.quickStatus', async () => {
    const token = await treeDataProvider.getToken();
    if (!token) {
      const choice = await vscode.window.showInformationMessage(
        'DB Health Monitor: No has iniciado sesión.',
        'Conectar Token',
        'Iniciar Sesión'
      );
      if (choice === 'Conectar Token') vscode.commands.executeCommand('dbhealth.setToken');
      if (choice === 'Iniciar Sesión') vscode.commands.executeCommand('dbhealth.login');
      return;
    }

    if (treeDataProvider.databases.length === 0) {
      const choice = await vscode.window.showInformationMessage(
        'DB Health Monitor: Aún no tienes bases de datos registradas.',
        'Registrar en la Web'
      );
      if (choice === 'Registrar en la Web') vscode.commands.executeCommand('dbhealth.createDatabase');
      return;
    }

    const items = treeDataProvider.databases.map((d) => ({
      label: `${d.engine === 'mongodb' ? '🍃' : '⚡'} ${d.name}`,
      description: `${d.engine.toUpperCase()} • cada ${d.interval_seconds}s`,
      detail: `ID: ${d.id}`
    }));

    const selected = await vscode.window.showQuickPick(items, {
      placeHolder: 'Selecciona una base de datos para ver en la web'
    });

    if (selected) {
      const dbId = selected.detail.replace('ID: ', '');
      vscode.commands.executeCommand('dbhealth.openDatabaseDetail', dbId);
    }
  });

  context.subscriptions.push(
    refreshCommand,
    loginCommand,
    setTokenCommand,
    logoutCommand,
    openDashboardCommand,
    createDatabaseCommand,
    openDatabaseDetailCommand,
    quickStatusCommand
  );

  // Auto-refresh en segundo plano cada 30 segundos
  const interval = setInterval(async () => {
    treeDataProvider.refresh();
    await updateStatusBar();
  }, 30000);

  context.subscriptions.push({ dispose: () => clearInterval(interval) });
}

function deactivate() {}

module.exports = {
  activate,
  deactivate
};
