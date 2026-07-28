param(
    [string]$Device = "windows",
    [string]$BackendUrl = "http://127.0.0.1:8000"
)

$ErrorActionPreference = "Stop"
$projectRoot = (Resolve-Path -LiteralPath (Join-Path $PSScriptRoot "..")).Path
$healthUrl = "$BackendUrl/health/readiness"

try {
    $readiness = Invoke-RestMethod -Uri $healthUrl -Method Get -TimeoutSec 5
} catch {
    throw "Backend is unavailable at $BackendUrl. Start it with scripts\start_backend.ps1 first."
}

if ($readiness.status -ne "ready") {
    throw "Backend readiness is '$($readiness.status)'. Check $healthUrl for details."
}

Set-Location -LiteralPath (Join-Path $projectRoot "app_flutter")
flutter pub get
if ($LASTEXITCODE -ne 0) {
    throw "flutter pub get failed."
}

Write-Host "Starting Flutter on '$Device' with backend $BackendUrl"
flutter run -d $Device --dart-define="BACKEND_URL=$BackendUrl"
