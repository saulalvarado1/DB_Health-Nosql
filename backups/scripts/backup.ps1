<#
.SYNOPSIS
    Script automatizado de respaldo (Backup) para PostgreSQL en DB Health Monitor.
.DESCRIPTION
    Genera un volcado completo consistente mediante pg_dump en formato Custom (-Fc),
    calcula su hash de integridad SHA-256 y aplica rotación automática de retención.
.PARAMETER DbName
    Nombre de la base de datos a respaldar (default: db_health_monitor).
.PARAMETER DbUser
    Usuario administrador/propietario de la base de datos (default: db_health_app).
.PARAMETER RetentionDays
    Días de retención para rotación de backups (default: 7 días).
#>
param(
    [string]$DbName = "db_health_monitor",
    [string]$DbUser = "db_health_app",
    [string]$ContainerName = "",
    [int]$RetentionDays = 7
)

$ErrorActionPreference = "Stop"
$ScriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path
$BaseDir = Split-Path -Parent $ScriptDir
$StorageDir = Join-Path $BaseDir "storage"
$LogDir = Join-Path $BaseDir "logs"

# Crear directorios si no existen
if (!(Test-Path $StorageDir)) { New-Item -ItemType Directory -Path $StorageDir | Out-Null }
if (!(Test-Path $LogDir)) { New-Item -ItemType Directory -Path $LogDir | Out-Null }

$Timestamp = Get-Date -Format "yyyyMMdd_HHmmss"
$BackupFileName = "${DbName}_${Timestamp}.dump"
$BackupFilePath = Join-Path $StorageDir $BackupFileName
$LogFilePath = Join-Path $LogDir "backup_${Timestamp}.log"

function Log-Message([string]$Message, [string]$Color = "White") {
    $LogEntry = "[$(Get-Date -Format 'yyyy-MM-dd HH:mm:ss')] $Message"
    Write-Host $LogEntry -ForegroundColor $Color
    Add-Content -Path $LogFilePath -Value $LogEntry
}

Log-Message "=========================================================" "Cyan"
Log-Message "    INICIANDO RESPALDO AUTOMATICO DE BASE DE DATOS       " "Cyan"
Log-Message "=========================================================" "Cyan"
Log-Message "Base de datos objetivo: $DbName" "Yellow"
Log-Message "Archivo de destino: $BackupFileName" "Yellow"

# 1. Detectar contenedor de Docker si no se especificó
if ([string]::IsNullOrWhiteSpace($ContainerName)) {
    $Detected = docker ps --filter "ancestor=postgres" --format "{{.Names}}" 2>$null | Select-Object -First 1
    if (!$Detected) {
        $Detected = docker ps --filter "name=postgres" --format "{{.Names}}" 2>$null | Select-Object -First 1
    }
    $ContainerName = $Detected
}

$Success = $false

if (![string]::IsNullOrWhiteSpace($ContainerName)) {
    Log-Message "Contenedor PostgreSQL detectado: $ContainerName" "Green"
    Log-Message "Ejecutando pg_dump en contenedor Docker..." "Cyan"
    
    # Ejecutar pg_dump dentro del contenedor y redirigir el stream binario
    docker exec $ContainerName pg_dump -U $DbUser -d $DbName -Fc -b -v > $BackupFilePath 2>> $LogFilePath
    if ($LASTEXITCODE -eq 0 -and (Test-Path $BackupFilePath) -and ((Get-Item $BackupFilePath).Length -gt 0)) {
        $Success = $true
    }
} else {
    Log-Message "Contenedor Docker no encontrado. Intentando con pg_dump local..." "Yellow"
    if (Get-Command pg_dump -ErrorAction SilentlyContinue) {
        pg_dump -U $DbUser -d $DbName -Fc -b -v -f $BackupFilePath 2>> $LogFilePath
        if ($LASTEXITCODE -eq 0) { $Success = $true }
    } else {
        Log-Message "ERROR: No se encontro pg_dump ni contenedor Docker de PostgreSQL." "Red"
        exit 1
    }
}

if ($Success) {
    $FileSize = (Get-Item $BackupFilePath).Length
    $FileSizeKB = [math]::Round($FileSize / 1KB, 2)
    Log-Message "Respaldo generado exitosamente ($FileSizeKB KB)." "Green"

    # 2. Generar Checksum SHA-256 para verificación de integridad
    $Hash = (Get-FileHash -Path $BackupFilePath -Algorithm SHA256).Hash
    $HashFilePath = "${BackupFilePath}.sha256"
    Set-Content -Path $HashFilePath -Value "$Hash  $BackupFileName"
    Log-Message "Checksum SHA-256 calculado: $Hash" "Gray"

    # 3. Aplicar Política de Rotación y Limpieza (Retention Policy)
    Log-Message "Verificando politica de retencion ($RetentionDays dias)..." "Cyan"
    $LimitDate = (Get-Date).AddDays(-$RetentionDays)
    $OldBackups = Get-ChildItem -Path $StorageDir -Filter "*.dump" | Where-Object { $_.CreationTime -lt $LimitDate }

    if ($OldBackups) {
        foreach ($Old in $OldBackups) {
            $OldName = $Old.Name
            Remove-Item $Old.FullName -Force
            $OldHash = Join-Path $StorageDir "${OldName}.sha256"
            if (Test-Path $OldHash) { Remove-Item $OldHash -Force }
            Log-Message "Rotacion: eliminado respaldo antiguo $OldName" "Yellow"
        }
    } else {
        Log-Message "No hay respaldos antiguos que superen la retencion." "Gray"
    }

    Log-Message "OPERACION COMPLETADA EXITOSAMENTE." "Green"
} else {
    Log-Message "ERROR: Fallo la generacion del respaldo. Consulte $LogFilePath" "Red"
    exit 1
}
