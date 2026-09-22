[CmdletBinding()]
param(
    [string]$OutputPath = (Join-Path (Split-Path $PSScriptRoot -Parent) ".env.deploy")
)

Set-StrictMode -Version Latest
$ErrorActionPreference = "Stop"

if (Test-Path -LiteralPath $OutputPath) {
    throw "El archivo ya existe y no se reemplazará: $OutputPath"
}

function New-RandomBytes([int]$Length) {
    $bytes = New-Object byte[] $Length
    $generator = [Security.Cryptography.RandomNumberGenerator]::Create()
    try {
        $generator.GetBytes($bytes)
    }
    finally {
        $generator.Dispose()
    }
    return $bytes
}

function ConvertTo-Hex([byte[]]$Bytes) {
    return ([BitConverter]::ToString($Bytes) -replace "-", "").ToLowerInvariant()
}

$postgresPassword = ConvertTo-Hex (New-RandomBytes 24)
$jwtSecret = ConvertTo-Hex (New-RandomBytes 48)
$fernetKey = [Convert]::ToBase64String((New-RandomBytes 32)).Replace("+", "-").Replace("/", "_")

$lines = @(
    "COMPOSE_PROJECT_NAME=db-health-monitor"
    "IMAGE_TAG=local"
    "APP_BIND_ADDRESS=127.0.0.1"
    "APP_PORT=8080"
    ""
    "POSTGRES_DB=db_health_monitor"
    "POSTGRES_USER=db_health_app"
    "POSTGRES_PASSWORD=$postgresPassword"
    "DATABASE_URL=postgresql+psycopg://db_health_app:$postgresPassword@postgres:5432/db_health_monitor"
    ""
    "JWT_SECRET_KEY=$jwtSecret"
    "CREDENTIALS_ENCRYPTION_KEY=$fernetKey"
    "LOG_LEVEL=INFO"
    "MONITORING_WORKER_POLL_SECONDS=5"
    "MONITORING_LEASE_SECONDS=90"
    "MONITORING_WORKER_BATCH_SIZE=25"
)

$utf8WithoutBom = New-Object Text.UTF8Encoding $false
[IO.File]::WriteAllLines($OutputPath, $lines, $utf8WithoutBom)

$postgresPassword = $null
$jwtSecret = $null
$fernetKey = $null

Write-Output "Configuración creada en $OutputPath. No compartas ni confirmes este archivo."
