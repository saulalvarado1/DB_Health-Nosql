[CmdletBinding()]
param(
    [ValidateRange(1, 65535)]
    [int]$PostgresPort = 55432,
    [ValidateRange(1, 65535)]
    [int]$RedisPort = 6381,
    [ValidateRange(1, 65535)]
    [int]$MongoPort = 27019
)

Set-StrictMode -Version Latest
$ErrorActionPreference = "Stop"

$dockerCommand = Get-Command docker -ErrorAction SilentlyContinue
if ($null -ne $dockerCommand) {
    $docker = $dockerCommand.Source
}
else {
    $docker = Join-Path $env:LOCALAPPDATA `
        "Programs\DockerDesktop\resources\bin\docker.exe"
    if (-not (Test-Path -LiteralPath $docker)) {
        throw "No se encontró Docker Desktop ni el comando docker."
    }
}
$python = Join-Path $PSScriptRoot "..\.venv\Scripts\python.exe"
if (-not (Test-Path -LiteralPath $python)) {
    throw "No se encontró el entorno virtual en backend\.venv."
}

$containers = @{
    postgres = "db-health-real-postgres"
    redis = "db-health-real-redis"
    mongodb = "db-health-real-mongodb"
}
$createdContainers = [System.Collections.Generic.List[string]]::new()

function New-RandomPassword {
    $bytes = New-Object byte[] 24
    $generator = [Security.Cryptography.RandomNumberGenerator]::Create()
    try {
        $generator.GetBytes($bytes)
    }
    finally {
        $generator.Dispose()
    }
    return ([BitConverter]::ToString($bytes) -replace "-", "").ToLowerInvariant()
}

function Assert-ContainerNameAvailable([string]$Name) {
    $existing = & $docker ps -a --filter "name=^/$Name$" --format "{{.Names}}"
    if ($existing -eq $Name) {
        throw "Ya existe un contenedor llamado $Name. No se modificó ni eliminó."
    }
}

function Wait-ForService([scriptblock]$Probe, [string]$Description, [int]$Attempts = 60) {
    for ($attempt = 0; $attempt -lt $Attempts; $attempt++) {
        try {
            & $Probe
        }
        catch {
            # El servicio puede rechazar conexiones durante sus primeros segundos.
            # El código de salida decide si corresponde reintentar.
        }
        if ($LASTEXITCODE -eq 0) {
            return
        }
        Start-Sleep -Seconds 1
    }
    throw "$Description no quedó disponible dentro del plazo."
}

foreach ($containerName in $containers.Values) {
    Assert-ContainerNameAvailable $containerName
}

$postgresPassword = New-RandomPassword
$redisPassword = New-RandomPassword
$mongoRootPassword = New-RandomPassword
$mongoMonitorPassword = New-RandomPassword

try {
    & $docker run `
        --name $containers.postgres `
        --label com.db-health-monitor.test=true `
        --detach `
        --publish "127.0.0.1:${PostgresPort}:5432" `
        --env POSTGRES_DB=db_health_monitor_test `
        --env POSTGRES_USER=db_health_test_app `
        --env "POSTGRES_PASSWORD=$postgresPassword" `
        postgres:18.6-alpine3.24 | Out-Null
    if ($LASTEXITCODE -ne 0) {
        throw "No se pudo crear PostgreSQL de integración."
    }
    $createdContainers.Add($containers.postgres)

    & $docker run `
        --name $containers.redis `
        --label com.db-health-monitor.test=true `
        --detach `
        --publish "127.0.0.1:${RedisPort}:6379" `
        redis:8.10.1-alpine `
        redis-server `
        --maxmemory 64mb `
        --maxmemory-policy noeviction `
        --appendonly no | Out-Null
    if ($LASTEXITCODE -ne 0) {
        throw "No se pudo crear Redis de integración."
    }
    $createdContainers.Add($containers.redis)

    & $docker run `
        --name $containers.mongodb `
        --label com.db-health-monitor.test=true `
        --detach `
        --publish "127.0.0.1:${MongoPort}:27017" `
        --env MONGO_INITDB_ROOT_USERNAME=root `
        --env "MONGO_INITDB_ROOT_PASSWORD=$mongoRootPassword" `
        mongo:8.0.32-noble | Out-Null
    if ($LASTEXITCODE -ne 0) {
        throw "No se pudo crear MongoDB de integración."
    }
    $createdContainers.Add($containers.mongodb)

    Wait-ForService `
        { & $docker exec $containers.postgres pg_isready -U db_health_test_app -d db_health_monitor_test *> $null } `
        "PostgreSQL"
    Wait-ForService `
        { & $docker exec $containers.redis redis-cli PING *> $null } `
        "Redis"
    Wait-ForService `
        {
            & $docker exec $containers.mongodb mongosh `
                --quiet `
                --username root `
                --password $mongoRootPassword `
                --authenticationDatabase admin `
                --eval "db.adminCommand({ping:1}).ok" *> $null
        } `
        "MongoDB"

    & $docker exec $containers.redis redis-cli ACL SETUSER monitor `
        on ">$redisPassword" -@all +ping +info | Out-Null
    if ($LASTEXITCODE -ne 0) {
        throw "No se pudo crear el usuario monitor de Redis."
    }
    & $docker exec $containers.redis redis-cli ACL SETUSER default off | Out-Null
    if ($LASTEXITCODE -ne 0) {
        throw "No se pudo desactivar el usuario default de Redis."
    }

    $createMongoMonitor = "db.getSiblingDB('admin').createUser(" +
        "{user:'monitor',pwd:'$mongoMonitorPassword'," +
        "roles:[{role:'clusterMonitor',db:'admin'}]})"
    & $docker exec $containers.mongodb mongosh `
        --quiet `
        --username root `
        --password $mongoRootPassword `
        --authenticationDatabase admin `
        --eval $createMongoMonitor | Out-Null
    if ($LASTEXITCODE -ne 0) {
        throw "No se pudo crear el usuario monitor de MongoDB."
    }

    $encodedPostgresPassword = [uri]::EscapeDataString($postgresPassword)
    $encodedRedisPassword = [uri]::EscapeDataString($redisPassword)
    $encodedMongoPassword = [uri]::EscapeDataString($mongoMonitorPassword)
    $env:DATABASE_URL = "postgresql+psycopg://db_health_test_app:" +
        "$encodedPostgresPassword@127.0.0.1:${PostgresPort}/db_health_monitor_test"
    $env:TEST_DATABASE_URL = $env:DATABASE_URL
    $env:TEST_REDIS_URI = "redis://monitor:$encodedRedisPassword@127.0.0.1:${RedisPort}/0"
    $env:TEST_MONGODB_URI = "mongodb://monitor:$encodedMongoPassword@" +
        "127.0.0.1:${MongoPort}/admin?authSource=admin"

    Push-Location (Join-Path $PSScriptRoot "..")
    try {
        & $python -m alembic upgrade head
        if ($LASTEXITCODE -ne 0) {
            throw "Alembic no pudo preparar PostgreSQL de integración."
        }
        & $python -m pytest -m integration -vv
        if ($LASTEXITCODE -ne 0) {
            throw "Las pruebas de integración fallaron."
        }
    }
    finally {
        Pop-Location
    }
}
finally {
    Remove-Item Env:DATABASE_URL -ErrorAction SilentlyContinue
    Remove-Item Env:TEST_DATABASE_URL -ErrorAction SilentlyContinue
    Remove-Item Env:TEST_REDIS_URI -ErrorAction SilentlyContinue
    Remove-Item Env:TEST_MONGODB_URI -ErrorAction SilentlyContinue

    foreach ($containerName in $createdContainers) {
        & $docker rm -f $containerName *> $null
    }

    $postgresPassword = $null
    $redisPassword = $null
    $mongoRootPassword = $null
    $mongoMonitorPassword = $null
}

Write-Output "Integración real finalizada; los contenedores temporales fueron eliminados."
