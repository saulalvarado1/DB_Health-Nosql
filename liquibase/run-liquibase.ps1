<#
.SYNOPSIS
    Ejecuta Liquibase usando el contenedor oficial de Docker.
.DESCRIPTION
    Aplica las migraciones pendientes en PostgreSQL o genera reportes sin necesidad
    de instalar Java ni Liquibase en Windows.
.PARAMETER Action
    Acción de Liquibase a ejecutar: 'update', 'status', 'rollback', 'history', o 'generate-report'.
#>
param(
    [ValidateSet("update", "status", "history", "generate-report")]
    [string]$Action = "update",

    [string]$DbHost = "localhost",
    [int]$DbPort = 5432,
    [string]$DbName = "db_health_monitor",
    [string]$DbUser = "db_health_app",
    [string]$DbPass = "db_health_secret"
)

$ErrorActionPreference = "Stop"
$ScriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path

Write-Host "=========================================================" -ForegroundColor Cyan
Write-Host "     LIQUIBASE MIGRATION RUNNER — DB HEALTH MONITOR      " -ForegroundColor Cyan
Write-Host "=========================================================" -ForegroundColor Cyan
Write-Host "Acción solicitada: $Action" -ForegroundColor Yellow
Write-Host "Destino: jdbc:postgresql://${DbHost}:${DbPort}/${DbName}" -ForegroundColor Yellow
Write-Host ""

$JdbcUrl = "jdbc:postgresql://${DbHost}:${DbPort}/${DbName}"

if ($Action -eq "generate-report") {
    $ReportPath = Join-Path $ScriptDir "report\liquibase-execution-report.html"
    $OutputDir = Join-Path $ScriptDir "report"
    if (!(Test-Path $OutputDir)) { New-Item -ItemType Directory -Path $OutputDir | Out-Null }

    Write-Host "Generando reporte de ejecución HTML..." -ForegroundColor Green
    docker run --rm `
        -v "${ScriptDir}:/liquibase/workspace" `
        --network host `
        liquibase/liquibase:4.29.2 `
        --searchPath=/liquibase/workspace `
        --defaults-file=/liquibase/workspace/liquibase.properties `
        --url="$JdbcUrl" `
        --username="$DbUser" `
        --password="$DbPass" `
        --changeLogFile=changelog/db.changelog-master.xml `
        history
    
    Write-Host "Reporte generado en: $ReportPath" -ForegroundColor Green
} else {
    docker run --rm `
        -v "${ScriptDir}:/liquibase/workspace" `
        --network host `
        liquibase/liquibase:4.29.2 `
        --searchPath=/liquibase/workspace `
        --defaults-file=/liquibase/workspace/liquibase.properties `
        --url="$JdbcUrl" `
        --username="$DbUser" `
        --password="$DbPass" `
        --changeLogFile=changelog/db.changelog-master.xml `
        $Action
}

Write-Host ""
Write-Host "Operación de Liquibase completada con éxito." -ForegroundColor Green
