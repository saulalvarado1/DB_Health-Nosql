# 🔌 DB Health Monitor — Extensión Oficial de Visual Studio Code

Extensión para Visual Studio Code que integra la observabilidad proactiva y el diagnóstico de salud determinista de **MongoDB** y **Redis** directamente en el editor del desarrollador y DBA.

---

## ✨ Características Principales

1. **Indicador en la Barra de Estado (Status Bar):**
   * Muestra en tiempo real el indicador global de salud: `$(database) DB Health: 100/100 (Saludable)`.
   * Al hacer clic, abre un menú desplegable interactivo (*QuickPick*) con el detalle de latencia, memoria y conexiones.

2. **Panel en la Barra de Actividades (Activity Bar):**
   * Un explorador visual en el lateral izquierdo con el icono de base de datos.
   * Lista todas las bases de datos monitoreadas con indicadores semafóricos:
     - 🟢 **Saludable** (Score: 80 - 100)
     - 🟡 **Advertencia** (Score: 50 - 79)
     - 🔴 **Crítico** (Score: 0 - 49)
   * Nodos desplegables con telemetría en vivo: latencia en milisegundos, consumo de RAM, conexiones concurrentes y estado de réplica.

3. **Comandos Integrados en la Paleta (`Ctrl + Shift + P`):**
   * `DB Health: Refrescar Estado`: Fuerza una sincronización inmediata con el backend.
   * `DB Health: Abrir Dashboard Web`: Abre el panel web interactivo en el navegador por defecto.
   * `DB Health: Mostrar Resumen de Salud`: Despliega la tarjeta rápida de telemetría.

---

## 🚀 Instalación y Uso Rápido en VS Code

### Opción 1: Probar en Modo Desarrollo (F5)
1. Abre la carpeta `vscode-extension/` en Visual Studio Code.
2. Presiona `F5` (o selecciona *Run Extension* en el panel de depuración).
3. Se abrirá una ventana de *Extension Development Host* con el monitor activo en la barra inferior y en la barra lateral.

### Opción 2: Instalación Local en tu VS Code
Para instalar la extensión de forma permanente en tu máquina:
```bash
# Copiar al directorio de extensiones de VS Code
cp -r vscode-extension ~/.vscode/extensions/db-health-monitor-1.0.0
```
O empaquetar con `vsce`:
```bash
npx vsce package
code --install-extension db-health-monitor-1.0.0.vsix
```

---

## ⚙️ Configuración (`settings.json`)

Puedes personalizar la extensión desde la configuración de VS Code:

```json
{
  "dbhealth.apiUrl": "https://dbhealth.alvarado1.tech",
  "dbhealth.autoRefreshSeconds": 30
}
```

---

## 🏛️ Información Institucional
* **Institución:** Universidad Privada de Tacna (UPT)
* **Curso:** SI-783 Base de Datos II (2026-II)
* **Equipo:** Grupo 3
