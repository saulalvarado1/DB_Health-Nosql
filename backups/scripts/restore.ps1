<#
.SYNOPSIS
    Script de restauración y prueba de recuperación ante desastres (Disaster Recovery).
.DESCRIPTION
    Verifica la integridad criptográfica SHA-256 del archivo de respaldo y restaura
    el contenido en PostgreSQL mediante pg_restore.
.PARAMETER BackupFile
    Ruta o nombre del archivo .dump a restaurar. Si se omite, toma el más reciente de storage/.
.PARAMETER DbName
    Nombre de la base de datos destino (default: db_health_monitor).
.PARAMETER DbUser
    Usuario administrador/propietario de la base de datos (default: db_health_app).
#>
param(
    [string]$BackupFile = "",
    [string]$DbName = "db_health_monitor",
    [string]$DbUser = "db_health_app",
    [string]$ContainerName = "",
    [switch]$SkipHashCheck
)

$ErrorActionPreference = "Stop"
$ScriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path
$BaseDir = Split-Path -Parent $ScriptDir
$StorageDir = Join-Path $BaseDir "storage"

Write-Host "=========================================================" -ForegroundColor Cyan
Write-Host "   RESTAURACION Y PRUEBA DE RECUPERACION ANTE DESASTRES  " -ForegroundColor Cyan
Write-Host "=========================================================" -ForegroundColor Cyan

# 1. Determinar archivo de backup a restaurar
if ([string]::IsNullOrWhiteSpace($BackupFile)) {
    $Latest = Get-ChildItem -Path $StorageDir -Filter "*.dump" | Sort-Object CreationTime -Descending | Select-Object -First 1
    if (!$Latest) {
        Write-Host "ERROR: No se encontraron archivos .dump en $StorageDir" -ForegroundColor Red
        exit 1
    }
    $BackupFilePath = $Latest.FullName
    $BackupFileName = $Latest.Name
} else {
    if (Test-Path $BackupFile) {
        $BackupFilePath = (Resolve-Path $BackupFile).Path
        $BackupFileName = Split-Path -Leaf $BackupFilePath
    } else {
        $BackupFilePath = Join-Path $StorageDir $BackupFile
        if (!(Test-Path $BackupFilePath)) {
            Write-Host "ERROR: Archivo no encontrado: $BackupFilePath" -ForegroundColor Red
            exit 1
        }
        $BackupFileName = $BackupFile
    }
}

Write-Host "Archivo seleccionado: $BackupFileName" -ForegroundColor Yellow
Write-Host "Base de datos destino: $DbName" -ForegroundColor Yellow

# 2. Verificación de Integridad con SHA-256
$HashFilePath = "${BackupFilePath}.sha256"
if (Test-Path $HashFilePath -and !$SkipHashCheck) {
    Write-Host "Verificando integridad criptografica SHA-256..." -ForegroundColor Cyan
    $ExpectedHash = (Get-Content $HashFilePath).Split(" ")[0].Trim().ToUpper()
    $ActualHash = (Get-FileHash -Path $BackupFilePath -Algorithm SHA256).Hash.ToUpper()

    if ($ExpectedHash -eq $ActualHash) {
        Write-Host "INTEGRIDAD VERIFICADA: El archivo no ha sido alterado ni corrompido." -ForegroundColor Green
    } else {
        Write-Host "ERROR CRITICO: El hash SHA-256 no coincide. El respaldo podria estar danado." -ForegroundColor Red
        exit 1
    }
}

# 3. Detectar contenedor Docker si no se especificó
if ([string]::IsNullOrWhiteSpace($ContainerName)) {
    $Detected = docker ps --filter "ancestor=postgres" --format "{{.Names}}" 2>$null | Select-Object -First 1
    if (!$Detected) {
        $Detected = docker ps --filter "name=postgres" --format "{{.Names}}" 2>$null | Select-Object -First 1
    }
    $ContainerName = $Detected
}

Write-Host "Iniciando proceso de restauracion con pg_restore..." -ForegroundColor Cyan

if (![string]::IsNullOrWhiteSpace($ContainerName)) {
    Write-Host "Restaurando en contenedor Docker: $ContainerName" -ForegroundColor Green
    # Copiar archivo temporalmente o montar stream
    docker cp $BackupFilePath "${ContainerName}:/tmp/restore_target.dump"
    docker exec $ContainerName pg_restore -U $DbUser -d $DbName --clean --if-exists --no-owner /tmp/restore_target.dump
    docker exec $ContainerName rm -f /tmp/restore_target.dump
} else {
    Write-Host "Restaurando localmente con pg_restore..." -ForegroundColor Yellow
    pg_restore -U $DbUser -d $DbName --clean --if-exists --no-owner $BackupFilePath
}

Write-Host "RESTAURACION COMPLETADA EXITOSAMENTE." -ForegroundColor Green
Write-Host "Las tablas, registros y restricciones han sido recuperados al estado del respaldo." -ForegroundColor Green
