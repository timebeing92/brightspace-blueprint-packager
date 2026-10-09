# One-terminal launcher for the Blueprint Packager (Windows, PowerShell 5.1+ or 7):
#     powershell -NoProfile -ExecutionPolicy Bypass -File blueprint_packager.ps1
# or double-click "Blueprint Packager.bat".
# Finds Python 3.11+, creates a private .venv inside this folder on first run
# (asking first), installs requirements.txt into it, then starts the runner.
# Follows the Blueprint Wizard runner's blueprint_wizard.ps1
# (brightspace-blueprint-runner, commit 85cef27).
$ErrorActionPreference = "Stop"
$Here = Split-Path -Parent $MyInvocation.MyCommand.Path
$MinVersion = [Version]"3.11"
$AssumeYes = ($args -contains "--yes") -or ($args -contains "-y")
$StayHere = ($args -contains "--here") -or ($env:BPK_NO_FORWARD -eq "1")

# A newer version installed beside this one takes over (launcher/install_release.py
# writes the pointer), unless --here or BPK_NO_FORWARD=1 says to stay.
$Pointer = Join-Path (Split-Path -Parent $Here) ".blueprint-packager-current"
if (-not $StayHere -and (Test-Path $Pointer)) {
    $Name = (Get-Content $Pointer -First 1).Trim()
    $Current = Join-Path (Split-Path -Parent $Here) $Name
    if ($Name -and ($Current -ne $Here) -and (Test-Path (Join-Path $Current "blueprint_packager.ps1"))) {
        Write-Host "  Starting the current version in $Name (pass --here to stay with this one)."
        $env:BPK_NO_FORWARD = "1"
        & powershell -NoProfile -ExecutionPolicy Bypass -File (Join-Path $Current "blueprint_packager.ps1") @args
        exit $LASTEXITCODE
    }
}

function Read-YesNo([string]$Prompt, [bool]$Default = $false) {
    if ($AssumeYes) { return $true }
    $suffix = if ($Default) { "[Y/n]" } else { "[y/N]" }
    $reply = Read-Host "$Prompt $suffix"
    if ([string]::IsNullOrWhiteSpace($reply)) { return $Default }
    return $reply -match "^(y|yes)$"
}

function Test-Python([string[]]$Command) {
    try {
        $probeArgs = @()
        if ($Command.Count -gt 1) { $probeArgs = @($Command[1..($Command.Count - 1)]) }
        $probeArgs += @("-c", "import sys; print('.'.join(map(str, sys.version_info[:2])))")
        $probe = & $Command[0] @probeArgs 2>$null
        if ($LASTEXITCODE -eq 0 -and $probe) { return ([Version]("$probe".Trim()) -ge $MinVersion) }
    } catch { }
    return $false
}

function Find-Python {
    $candidates = @()
    if ($env:PYTHON) { $candidates += ,@($env:PYTHON) }
    if (Get-Command py -ErrorAction SilentlyContinue) {
        foreach ($ver in "-3.14", "-3.13", "-3.12", "-3.11", "-3") { $candidates += ,@("py", $ver) }
    }
    foreach ($cmd in "python3", "python") {
        if (Get-Command $cmd -ErrorAction SilentlyContinue) { $candidates += ,@($cmd) }
    }
    foreach ($candidate in $candidates) {
        if (Test-Python $candidate) {
            $prefix = @()
            if ($candidate.Count -gt 1) { $prefix = @($candidate[1..($candidate.Count - 1)]) }
            return [PSCustomObject]@{ Executable = [string]$candidate[0]; PrefixArguments = [string[]]$prefix }
        }
    }
    return $null
}

$Python = Find-Python
if (-not $Python) {
    Write-Host "Python 3.11 or later was not found."
    if ((Get-Command winget -ErrorAction SilentlyContinue) -and (Read-YesNo "Install Python with winget now?" $true)) {
        winget install --id Python.Python.3.12 -e --source winget
        $Python = Find-Python
    } else {
        Write-Host "Install Python 3.11+ from https://www.python.org/downloads/ (check 'Add python.exe to PATH'), then rerun this launcher."
    }
    if (-not $Python) {
        Write-Host "Python 3.11+ is still not on PATH in this window. Open a new terminal and rerun this launcher." -ForegroundColor Yellow
        exit 1
    }
}

$VenvPython = Join-Path $Here ".venv\Scripts\python.exe"
if (-not (Test-Path $VenvPython)) {
    Write-Host "First run: the packager keeps its Python packages in a private folder, $Here\.venv."
    if (Read-YesNo "Create it and install the packages from requirements.txt now?" $true) {
        & $Python.Executable @($Python.PrefixArguments) -m venv (Join-Path $Here ".venv")
        & $VenvPython -m pip install --quiet --upgrade pip
        & $VenvPython -m pip install --quiet -r (Join-Path $Here "requirements.txt")
    } else {
        Write-Host "Running with the system Python instead; the runner will say if a package is missing."
        & $Python.Executable @($Python.PrefixArguments) (Join-Path $Here "scripts\packager_tui.py") @args
        exit $LASTEXITCODE
    }
}

& $VenvPython (Join-Path $Here "scripts\packager_tui.py") @args
exit $LASTEXITCODE
