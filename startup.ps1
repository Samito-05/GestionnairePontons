param(
    [switch]$NoRunServer,
    [switch]$SkipInstall,
    [switch]$SkipDemo,
    [switch]$ResetDatabase,
    [int]$Port = 8000
)

Set-StrictMode -Version Latest
$ErrorActionPreference = "Stop"

$ProjectRoot = Split-Path -Parent $MyInvocation.MyCommand.Path
Set-Location $ProjectRoot

function Write-Step {
    param([string]$Message)
    Write-Host "`n==> $Message" -ForegroundColor Cyan
}

function Resolve-PythonCommand {
    if (Get-Command py -ErrorAction SilentlyContinue) {
        return "py -3"
    }
    if (Get-Command python -ErrorAction SilentlyContinue) {
        return "python"
    }
    throw "Python 3 was not found. Install Python 3.10+ and try again."
}

Write-Host "GestionnairePontons startup" -ForegroundColor Green
Write-Host "Project root: $ProjectRoot"

$PythonCommand = Resolve-PythonCommand
$VenvPath = Join-Path $ProjectRoot "venv"
$ActivateScript = Join-Path $VenvPath "Scripts\Activate.ps1"

if (-not (Test-Path $ActivateScript)) {
    Write-Step "Creating virtual environment"
    Invoke-Expression "$PythonCommand -m venv venv"
}

Write-Step "Activating virtual environment"
& $ActivateScript

if (-not $SkipInstall) {
    Write-Step "Installing Python dependencies"
    python -m pip install --upgrade pip
    pip install -r requirements.txt
} else {
    Write-Step "Skipping dependency installation"
}

if ($ResetDatabase) {
    Write-Step "Resetting SQLite database"
    $DbPath = Join-Path $ProjectRoot "db.sqlite3"
    if (Test-Path $DbPath) {
        Remove-Item $DbPath -Force
        Write-Host "Removed db.sqlite3"
    } else {
        Write-Host "No db.sqlite3 file found"
    }
}

Write-Step "Applying migrations"
python manage.py migrate

if (-not $SkipDemo) {
    Write-Step "Loading demo data"
    python manage.py init_demo
} else {
    Write-Step "Skipping demo data initialization"
}

if ($NoRunServer) {
    Write-Step "Startup completed (server not started)"
    exit 0
}

Write-Step "Starting Django server on http://127.0.0.1:$Port"
python manage.py runserver "127.0.0.1:$Port"
