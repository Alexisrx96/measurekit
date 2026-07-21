# PHS Native CLI & REPL Installer for Windows (PowerShell & CMD)
# Usage in PowerShell:
#   irm https://physure.irvintorres.com/install.ps1 | iex
#
# Usage in CMD:
#   powershell -ExecutionPolicy Bypass -c "irm https://physure.irvintorres.com/install.ps1 | iex"

$ErrorActionPreference = 'Stop'

Write-Host "⚡ Installing Standalone PHS Native Executable for Windows..." -ForegroundColor Cyan

$BinDir = "$HOME\.phs\bin"
if (-not (Test-Path -Path $BinDir)) {
    New-Item -ItemType Directory -Path $BinDir -Force | Out-Null
}

$ExePath = "$BinDir\phs.exe"
$Installed = $false

# 1. Try cargo install if cargo is available
if (Get-Command cargo -ErrorAction SilentlyContinue) {
    Write-Host "📦 Rust cargo detected. Installing phs..." -ForegroundColor Yellow
    try {
        cargo install physure --bin phs | Out-Null
        $CargoExe = "$HOME\.cargo\bin\phs.exe"
        if (Test-Path $CargoExe) {
            Copy-Item -Path $CargoExe -Destination $ExePath -Force
            $Installed = $true
        }
    } catch {
        # continue to fallback
    }
}

# 2. Try fetching latest release from GitHub
if (-not $Installed) {
    Write-Host "📥 Downloading latest phs.exe release..." -ForegroundColor Yellow
    $ReleaseUrl = "https://github.com/Alexisrx96/physure/releases/latest/download/phs-windows-amd64.exe"
    try {
        Invoke-WebRequest -Uri $ReleaseUrl -OutFile $ExePath -UseBasicParsing
        $Installed = $true
    } catch {
        $CargoExe = "$HOME\.cargo\bin\phs.exe"
        if (Test-Path $CargoExe) {
            Copy-Item -Path $CargoExe -Destination $ExePath -Force
            $Installed = $true
        }
    }
}

if (-not $Installed) {
    Write-Error "Failed to install phs.exe. Please install Rust and run: cargo install physure --bin phs"
    exit 1
}

# Add $BinDir to User Environment PATH if not present
$UserPath = [Environment]::GetEnvironmentVariable("Path", "User")
if ($UserPath -notlike "*$BinDir*") {
    $NewPath = "$UserPath;$BinDir"
    [Environment]::SetEnvironmentVariable("Path", $NewPath, "User")
    $env:Path = "$env:Path;$BinDir"
    Write-Host "✨ Added $BinDir to User PATH environment variable." -ForegroundColor Green
}

Write-Host "`n🎉 PHS successfully installed!" -ForegroundColor Green
Write-Host "Try running: phs  or  phs `"500 N / 2 m^2 => kPa`"" -ForegroundColor Cyan
