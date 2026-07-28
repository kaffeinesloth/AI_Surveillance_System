param(
    [string]$BindAddress = "127.0.0.1",
    [int]$Port = 8000,
    [switch]$Reload
)

$ErrorActionPreference = "Stop"
$projectRoot = (Resolve-Path -LiteralPath (Join-Path $PSScriptRoot "..")).Path
Set-Location -LiteralPath $projectRoot

python -c "import fastapi, uvicorn, cv2; print('Backend dependencies OK')"
if ($LASTEXITCODE -ne 0) {
    throw "Backend dependencies are missing. Run: python -m pip install -r backend\requirements.txt"
}

$uvicornArguments = @(
    "-m", "uvicorn", "backend.main:app",
    "--host", $BindAddress,
    "--port", $Port.ToString()
)
if ($Reload) {
    $uvicornArguments += "--reload"
}

Write-Host "Starting backend at http://${BindAddress}:$Port"
python @uvicornArguments
