# One-command installer for the Blueprint Packager (Windows PowerShell).
#
#   powershell -NoProfile -ExecutionPolicy Bypass -File install_blueprint_packager.ps1 [folder]
#
# The repository is public. This fetches the latest release through the gh
# command when it is signed in, otherwise anonymously (checking the published
# SHA-256), and clones main with git only when no release can be reached.
# BPK_INSTALL_NO_START=1 installs without starting the runner.
# Fetches the latest release (or main when no release exists yet) into
# <folder>\brightspace-blueprint-packager-v<version>\, writes the pointer the
# launchers use, and starts the runner. Re-running installs a newer release
# beside the old one; nothing is deleted.
$ErrorActionPreference = "Stop"
$Repo = "timebeing92/brightspace-blueprint-packager"
$TargetDir = if ($args.Count -gt 0) { $args[0] } else { "blueprint-packager" }
New-Item -ItemType Directory -Force -Path $TargetDir | Out-Null
$Root = (Resolve-Path $TargetDir).Path

function Have-Gh {
    if (-not (Get-Command gh -ErrorAction SilentlyContinue)) { return $false }
    & gh auth status --hostname github.com 2>$null | Out-Null
    return ($LASTEXITCODE -eq 0)
}

$Tag = ""
$ZipUrl = ""
$ShaUrl = ""
$UseGh = Have-Gh
if ($UseGh) { try { $Tag = (& gh release view --repo $Repo --json tagName -q .tagName 2>$null).Trim() } catch { $Tag = "" } }
if (-not $Tag) {
    # the public release, read anonymously
    $UseGh = $false
    try {
        $Latest = Invoke-RestMethod -Uri "https://api.github.com/repos/$Repo/releases/latest" -Headers @{ Accept = "application/vnd.github+json"; "User-Agent" = "Blueprint-Packager-Installer" }
        $Tag = [string]$Latest.tag_name
        $ZipUrl = [string]($Latest.assets | Where-Object { $_.name -like "*.zip" } | Select-Object -First 1 -ExpandProperty browser_download_url)
        $ShaUrl = [string]($Latest.assets | Where-Object { $_.name -like "*.zip.sha256" } | Select-Object -First 1 -ExpandProperty browser_download_url)
        if (-not $ZipUrl) { $Tag = "" }
    } catch { $Tag = "" }
}

if ($Tag) {
    Write-Host "== downloading release $Tag"
    $Tmp = Join-Path ([System.IO.Path]::GetTempPath()) ("bpk-" + [guid]::NewGuid().ToString("N"))
    New-Item -ItemType Directory -Force -Path $Tmp | Out-Null
    if ($UseGh) {
        & gh release download $Tag --repo $Repo --pattern "*.zip" --pattern "*.zip.sha256" --dir $Tmp --clobber
    } else {
        Invoke-WebRequest -Uri $ZipUrl -OutFile (Join-Path $Tmp ([System.IO.Path]::GetFileName($ZipUrl)))
        if ($ShaUrl) { Invoke-WebRequest -Uri $ShaUrl -OutFile (Join-Path $Tmp ([System.IO.Path]::GetFileName($ShaUrl))) }
    }
    $Zip = Get-ChildItem $Tmp -Filter *.zip | Select-Object -First 1
    $Sidecar = Join-Path $Tmp ($Zip.Name + ".sha256")
    if (Test-Path $Sidecar) {
        $Expected = ((Get-Content $Sidecar -Raw).Trim() -split "\s+")[0].ToLower()
        $Actual = (Get-FileHash -Algorithm SHA256 $Zip.FullName).Hash.ToLower()
        if ($Expected -ne $Actual) { Write-Host "The download does not match its published SHA-256; stopping." -ForegroundColor Yellow; exit 1 }
        Write-Host "   SHA-256 matches the published sidecar"
    }
    Add-Type -AssemblyName System.IO.Compression.FileSystem
    $Archive = [System.IO.Compression.ZipFile]::OpenRead($Zip.FullName)
    $Top = ($Archive.Entries | Select-Object -First 1).FullName.Split("/")[0]
    $Archive.Dispose()
    if (Test-Path (Join-Path $Root $Top)) { Write-Host "   $Top is already installed." }
    else { Expand-Archive -Path $Zip.FullName -DestinationPath $Root; Write-Host "   unpacked $Top" }
    Remove-Item -Recurse -Force $Tmp
    Set-Content -Path (Join-Path $Root ".blueprint-packager-current") -Value $Top
    $Installed = Join-Path $Root $Top
} else {
    if (-not (Get-Command git -ErrorAction SilentlyContinue)) {
        Write-Host "git is required for this install path (or sign in with gh to download a release)." -ForegroundColor Yellow
        exit 1
    }
    $Name = "brightspace-blueprint-packager-main"
    if (Test-Path (Join-Path $Root "$Name\.git")) {
        Write-Host "== $Name is present; pulling main"
        & git -C (Join-Path $Root $Name) pull --ff-only
    } else {
        Write-Host "== no release could be reached (no gh signed in, and no network); cloning main"
        if (Have-Gh) { & gh repo clone $Repo (Join-Path $Root $Name) }
        else {
            & git clone "https://github.com/$Repo.git" (Join-Path $Root $Name)
            if ($LASTEXITCODE -ne 0) {
                Write-Host "The clone was refused: check the network, or sign in with 'gh auth login' and rerun." -ForegroundColor Yellow
                exit 1
            }
        }
    }
    Set-Content -Path (Join-Path $Root ".blueprint-packager-current") -Value $Name
    $Installed = Join-Path $Root $Name
}

@(
    "installed_at_utc=" + (Get-Date).ToUniversalTime().ToString("yyyy-MM-ddTHH:mm:ssZ"),
    "folder=$Installed",
    "release=" + $(if ($Tag) { $Tag } else { "main" })
) | Set-Content -Path (Join-Path $Root "INSTALL_RECEIPT.txt")

Write-Host ""
Write-Host "Installed into: $Installed"
Write-Host "Start it later by double-clicking 'Blueprint Packager.bat' in that folder."
Write-Host ""
if ($env:BPK_INSTALL_NO_START -eq "1") { exit 0 }
& powershell -NoProfile -ExecutionPolicy Bypass -File (Join-Path $Installed "blueprint_packager.ps1")
exit $LASTEXITCODE
