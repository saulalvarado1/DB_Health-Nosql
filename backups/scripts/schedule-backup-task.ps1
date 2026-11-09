<#
.SYNOPSIS
    Programa la tarea automática de respaldo diario en Windows Task Scheduler.
.DESCRIPTION
    Crea una tarea programada del sistema que ejecuta backup.ps1 todos los días a las 02:00 AM.
#>
param(
    [string]$TaskName = "DBHealthMonitor_DailyBackup",
    [string]$ExecutionTime = "02:00"
)

$ErrorActionPreference = "Stop"
$ScriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path
$BackupScriptPath = Join-Path $ScriptDir "backup.ps1"

Write-Host "=========================================================" -ForegroundColor Cyan
Write-Host " PROGRAMACION DE TAREA AUTOMATICA DE BACKUPS EN WINDOWS   " -ForegroundColor Cyan
Write-Host "=========================================================" -ForegroundColor Cyan
Write-Host "Tarea: $TaskName" -ForegroundColor Yellow
Write-Host "Hora de ejecucion: $ExecutionTime diaria" -ForegroundColor Yellow
Write-Host "Script: $BackupScriptPath" -ForegroundColor Yellow

$Action = New-ScheduledTaskAction -Execute "powershell.exe" -Argument "-ExecutionPolicy Bypass -File `"$BackupScriptPath`""
$Trigger = New-ScheduledTaskTrigger -Daily -At $ExecutionTime
$Settings = New-ScheduledTaskSettingsSet -AllowStartIfOnBatteries -DontStopIfGoingOnBatteries -StartWhenAvailable

try {
    Register-ScheduledTask -TaskName $TaskName -Action $Action -Trigger $Trigger -Settings $Settings -Description "Respaldo automatico diario de DB Health Monitor" -Force | Out-Null
    Write-Host ""
    Write-Host "TAREA PROGRAMADA CON EXITO: Se ejecutara automaticamente cada dia a las $ExecutionTime." -ForegroundColor Green
} catch {
    Write-Host "AVISO: Se requieren privilegios de Administrador para registrar tareas en Windows." -ForegroundColor Yellow
    Write-Host "Comando manual equivalente:" -ForegroundColor Cyan
    Write-Host "schtasks /create /tn `"$TaskName`" /tr `"powershell.exe -File \`"$BackupScriptPath\`"`" /sc daily /st $ExecutionTime /f" -ForegroundColor Gray
}
