[CmdletBinding()]
param(
    [ValidateRange(1, 65535)]
    [int]$Port = 18081,
    [switch]$SkipBrowserInstall
)

Set-StrictMode -Version Latest
$ErrorActionPreference = "Stop"

$repository = Split-Path $PSScriptRoot -Parent
$frontend = Join-Path $repository "frontend"
$compose = Join-Path $repository "compose.yaml"
$composeE2e = Join-Path $repository "compose.e2e.yaml"
$environmentGenerator = Join-Path $PSScriptRoot "generate-env.ps1"
$projectName = "db-health-e2e-" + [guid]::NewGuid().ToString("N").Substring(0, 10)
$temporaryDirectory = Join-Path ([IO.Path]::GetTempPath()) $projectName
$environmentFile = Join-Path $temporaryDirectory "environment.env"
$redisAclFile = Join-Path $temporaryDirectory "users.acl"
$stackCreated = $false
$composeArguments = @()

function Get-Executable([string]$Name, [string]$Fallback) {
    $command = Get-Command $Name -ErrorAction SilentlyContinue
    if ($null -ne $command) {
        return $command.Source
    }
    if (Test-Path -LiteralPath $Fallback) {
        return $Fallback
    }
    throw "No se encontró $Name."
}

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

$docker = Get-Executable "docker" (Join-Path $env:LOCALAPPDATA `
    "Programs\DockerDesktop\resources\bin\docker.exe")
$npm = Get-Executable "npm.cmd" (Join-Path $env:ProgramFiles "nodejs\npm.cmd")
$npx = Get-Executable "npx.cmd" (Join-Path $env:ProgramFiles "nodejs\npx.cmd")
$edgePath = Join-Path ${env:ProgramFiles(x86)} "Microsoft\Edge\Application\msedge.exe"
$chromePath = Join-Path $env:ProgramFiles "Google\Chrome\Application\chrome.exe"

if ($null -ne (Get-NetTCPConnection -LocalPort $Port -State Listen -ErrorAction SilentlyContinue)) {
    throw "El puerto $Port ya está ocupado. Usa -Port con otro valor."
}

$preexistingResources = @(
    @(& $docker ps -a --filter "label=com.docker.compose.project=$projectName" --format "{{.ID}}").Count
    @(& $docker network ls --filter "label=com.docker.compose.project=$projectName" --format "{{.ID}}").Count
    @(& $docker volume ls --filter "label=com.docker.compose.project=$projectName" --format "{{.Name}}").Count
)
if (($preexistingResources | Measure-Object -Sum).Sum -ne 0) {
    throw "El proyecto aislado $projectName ya tiene recursos y no se modificará."
}

$redisPassword = New-RandomPassword
$mongoRootPassword = New-RandomPassword
$mongoMonitorPassword = New-RandomPassword

try {
    New-Item -ItemType Directory -Path $temporaryDirectory | Out-Null
    & $environmentGenerator -OutputPath $environmentFile

    $aclLines = @(
        "user default off"
        "user monitor on >$redisPassword -@all +ping +info"
    )
    $utf8WithoutBom = New-Object Text.UTF8Encoding $false
    [IO.File]::WriteAllLines($redisAclFile, $aclLines, $utf8WithoutBom)

    $env:APP_PORT = [string]$Port
    $env:E2E_REDIS_ACL_FILE = $redisAclFile.Replace("\", "/")
    $env:E2E_REDIS_MONITOR_PASSWORD = $redisPassword
    $env:E2E_MONGO_ROOT_PASSWORD = $mongoRootPassword

    $composeArguments = @(
        "compose"
        "--env-file", $environmentFile
        "-f", $compose
        "-f", $composeE2e
        "-p", $projectName
    )

    & $docker @composeArguments config --quiet
    if ($LASTEXITCODE -ne 0) {
        throw "La composición E2E no es válida."
    }

    & $docker @composeArguments up --build --detach --wait --wait-timeout 240
    if ($LASTEXITCODE -ne 0) {
        throw "El entorno E2E no alcanzó estado saludable."
    }
    $stackCreated = $true

    $createMongoMonitor = "db.getSiblingDB('admin').createUser(" +
        "{user:'monitor',pwd:'$mongoMonitorPassword'," +
        "roles:[{role:'clusterMonitor',db:'admin'}]})"
    & $docker @composeArguments exec -T mongodb-e2e mongosh `
        --quiet `
        --username root `
        --password $mongoRootPassword `
        --authenticationDatabase admin `
        --eval $createMongoMonitor | Out-Null
    if ($LASTEXITCODE -ne 0) {
        throw "No se pudo crear el usuario de monitoreo de MongoDB."
    }

    $encodedRedisPassword = [uri]::EscapeDataString($redisPassword)
    $encodedMongoPassword = [uri]::EscapeDataString($mongoMonitorPassword)
    $env:E2E_BASE_URL = "http://127.0.0.1:$Port"
    $env:E2E_REDIS_URI = "redis://monitor:$encodedRedisPassword@redis-e2e:6379/0"
    $env:E2E_MONGODB_URI = "mongodb://monitor:$encodedMongoPassword@" +
        "mongodb-e2e:27017/admin?authSource=admin"

    if (Test-Path -LiteralPath $edgePath) {
        $env:E2E_BROWSER_CHANNEL = "msedge"
    }
    elseif (Test-Path -LiteralPath $chromePath) {
        $env:E2E_BROWSER_CHANNEL = "chrome"
    }

    Push-Location $frontend
    try {
        $playwrightCommand = Join-Path $frontend "node_modules\.bin\playwright.cmd"
        if (-not (Test-Path -LiteralPath $playwrightCommand)) {
            throw "Faltan dependencias del frontend. Ejecuta npm install en frontend."
        }
        if (-not $SkipBrowserInstall -and $null -eq $env:E2E_BROWSER_CHANNEL) {
            & $npx playwright install chromium
            if ($LASTEXITCODE -ne 0) {
                throw "No se pudo instalar Chromium para Playwright."
            }
        }
        & $npm run test:e2e
        if ($LASTEXITCODE -ne 0) {
            throw "La prueba E2E falló."
        }
    }
    finally {
        Pop-Location
    }
}
finally {
    if (Test-Path -LiteralPath $environmentFile) {
        $projectContainers = @(& $docker ps -a `
            --filter "label=com.docker.compose.project=$projectName" `
            --format "{{.ID}}")
        if ($stackCreated -or $projectContainers.Count -gt 0) {
            & $docker compose `
                --env-file $environmentFile `
                -f $compose `
                -f $composeE2e `
                -p $projectName `
                down --volumes --remove-orphans
        }
        Remove-Item -LiteralPath $environmentFile -Force
    }
    if (Test-Path -LiteralPath $redisAclFile) {
        Remove-Item -LiteralPath $redisAclFile -Force
    }
    if (Test-Path -LiteralPath $temporaryDirectory) {
        Remove-Item -LiteralPath $temporaryDirectory -Force
    }

    Remove-Item Env:APP_PORT -ErrorAction SilentlyContinue
    Remove-Item Env:E2E_REDIS_ACL_FILE -ErrorAction SilentlyContinue
    Remove-Item Env:E2E_REDIS_MONITOR_PASSWORD -ErrorAction SilentlyContinue
    Remove-Item Env:E2E_MONGO_ROOT_PASSWORD -ErrorAction SilentlyContinue
    Remove-Item Env:E2E_BASE_URL -ErrorAction SilentlyContinue
    Remove-Item Env:E2E_REDIS_URI -ErrorAction SilentlyContinue
    Remove-Item Env:E2E_MONGODB_URI -ErrorAction SilentlyContinue
    Remove-Item Env:E2E_BROWSER_CHANNEL -ErrorAction SilentlyContinue

    $redisPassword = $null
    $mongoRootPassword = $null
    $mongoMonitorPassword = $null
}

Write-Output "E2E finalizado; el entorno temporal fue eliminado."
