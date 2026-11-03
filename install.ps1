<#
  dotfiles-windows installieren (Windows 11, ohne Administratorrechte)

  .\install.ps1                 Configs verlinken/kopieren, wintheme einrichten, einmal einfärben
  .\install.ps1 -NoWatch        ohne Autostart von „wintheme --watch“
  .\install.ps1 -Uninstall      Originalfarben wiederherstellen und wintheme entfernen
  .\install.ps1 -Uninstall -KeepColors   wintheme entfernen, Farben behalten
  (Aufruf: powershell -ExecutionPolicy Bypass -File .\install.ps1)

  Nur für installierte Werkzeuge – fehlende (z. B. komorebi, whkd) werden übersprungen.
  Hardlinks (Änderungen landen direkt im Repo): komorebi, whkd, VS-Code-Tastenkürzel (geht ein Hardlink
  nicht, z. B. in OneDrive, wird kopiert). PowerShell-Profil: kleine Ladedatei, die das Profil aus dem Repo lädt.
  Einmal kopiert (wintheme trägt dort die Farben ein, das Repo bleibt sauber):
  Windows-Terminal- und VS-Code-settings.json. oh-my-posh-Theme wird von wintheme erzeugt.
#>
param([switch]$NoWatch, [switch]$Uninstall, [switch]$KeepColors)
$ErrorActionPreference = 'Stop'

# Protokoll für diagnose.ps1 (auch bei Abbruch durch einen Fehler)
$logDir = Join-Path $env:LOCALAPPDATA 'wintheme-logs'
New-Item -ItemType Directory -Force -Path $logDir | Out-Null
try { Start-Transcript -Path (Join-Path $logDir 'install.log') -Force | Out-Null } catch {}
trap {
    Write-Host "FEHLER: $_" -ForegroundColor Red
    Write-Host "  bei: $($_.InvocationInfo.PositionMessage)"
    Write-Host 'Für Hilfe: powershell -ExecutionPolicy Bypass -File .\diagnose.ps1'
    try { Stop-Transcript | Out-Null } catch {}
    break
}
$repo    = $PSScriptRoot
$Dest    = Join-Path $env:LOCALAPPDATA 'wintheme'
$Bin     = Join-Path $env:LOCALAPPDATA 'wintheme\bin'            # eigener Ordner im Benutzer-PATH
$Shim    = Join-Path $Bin 'wintheme.cmd'
$OldShim = Join-Path $env:LOCALAPPDATA 'Microsoft\WindowsApps\wintheme.cmd'   # frühere Versionen
$MenuKey = 'HKCU:\Software\Classes\SystemFileAssociations\image\shell\wintheme'
$Startup = Join-Path ([Environment]::GetFolderPath('Startup')) 'wintheme-watch.lnk'
$vpy     = Join-Path $Dest 'venv\Scripts\python.exe'
$vpyw    = Join-Path $Dest 'venv\Scripts\pythonw.exe'

function Stop-Watch {
    Get-Process pythonw -ErrorAction SilentlyContinue | Where-Object { $_.Path -like "$Dest*" } | Stop-Process -Force
}

# ── Deinstallieren ────────────────────────────────────────────────────────────
if ($Uninstall) {
    Stop-Watch
    if (-not $KeepColors -and (Test-Path $vpy)) {
        Write-Host 'Stelle den Zustand vor der ersten Benutzung wieder her …'
        & $vpy (Join-Path $Dest 'wintheme.py') --original
    }
    Remove-Item -Recurse -Force $Dest, $OldShim, $Startup -ErrorAction SilentlyContinue
    $userPath = [Environment]::GetEnvironmentVariable('Path', 'User')
    if ($userPath) {
        $rest = ($userPath -split ';' | Where-Object { $_ -and $_ -ne $Bin }) -join ';'
        [Environment]::SetEnvironmentVariable('Path', $rest, 'User')
    }
    Remove-Item -Recurse -Force $MenuKey -ErrorAction SilentlyContinue
    Write-Host 'wintheme entfernt (Einstellungen/Stände: %APPDATA%\wintheme). Verlinkte Configs bleiben.'
    try { Stop-Transcript | Out-Null } catch {}
    return
}

# ── 1. Configs ────────────────────────────────────────────────────────────────
function Link($source, $link) {
    $target = Join-Path $repo $source
    New-Item -ItemType Directory -Force -Path (Split-Path $link) | Out-Null
    if (Test-Path $link) { Remove-Item $link -Force }
    try {
        New-Item -ItemType HardLink -Path $link -Target $target -ErrorAction Stop | Out-Null
        Write-Host "LINK:  $link"
    } catch {
        # z. B. OneDrive: keine Hardlinks erlaubt → Kopie statt Abbruch
        Copy-Item $target $link -Force
        Write-Host "KOPIE: $link (Hardlink nicht möglich: $($_.Exception.Message))" -ForegroundColor Yellow
    }
}
# Profil: kleine Datei, die das Profil aus dem Repo lädt – funktioniert auch im OneDrive-Ordner
function LinkProfile($dest) {
    $src = Join-Path $repo '.config\powershell\Microsoft.PowerShell_profile.ps1'
    $marker = '# dotfiles-windows: lädt das Profil aus dem Repo'
    $stub = "$marker`r`n. '$src'`r`n"
    New-Item -ItemType Directory -Force -Path (Split-Path $dest) | Out-Null
    if (Test-Path $dest) {
        $old = Get-Content $dest -Raw -ErrorAction SilentlyContinue
        $repoText = Get-Content $src -Raw
        # eigene, fremde Profildatei sichern (nicht unser Lader, nicht die frühere Kopie/Link des Repo-Profils)
        if ($old -and -not $old.StartsWith($marker) -and $old -ne $repoText) {
            Copy-Item $dest "$dest.bak" -Force
            Write-Host "SICHERUNG: $dest.bak"
        }
        Remove-Item $dest -Force
    }
    [System.IO.File]::WriteAllText($dest, $stub, (New-Object System.Text.UTF8Encoding $true))
    Write-Host "PROFIL: $dest"
}
# Einmal kopieren: fehlt die Datei oder ist sie noch ein Hardlink aufs Repo (alte Installation) → Kopie;
# eine eigene, unabhängige Datei bleibt unangetastet
function CopyOnce($source, $dest) {
    $src = Join-Path $repo $source
    New-Item -ItemType Directory -Force -Path (Split-Path $dest) | Out-Null
    $isLink = (Test-Path $dest) -and ((Get-Item $dest).LinkType -eq 'HardLink')
    if (-not (Test-Path $dest) -or $isLink) {
        if ($isLink) { Remove-Item $dest -Force }
        Copy-Item $src $dest
        Write-Host "KOPIE: $dest"
    } else {
        Write-Host "BLEIBT: $dest (eigene Datei)"
    }
}

# Welche Werkzeuge sind da? (fehlende werden übersprungen)
function Has($cmd) { [bool](Get-Command $cmd -ErrorAction SilentlyContinue) }
$wtDir  = "$env:LOCALAPPDATA\Packages\Microsoft.WindowsTerminal_8wekyb3d8bbwe"
$tools = [ordered]@{
    'komorebi'         = (Has 'komorebic') -or (Has 'komorebi')
    'whkd'             = Has 'whkd'
    'VS Code'          = (Has 'code') -or (Test-Path "$env:LOCALAPPDATA\Programs\Microsoft VS Code\Code.exe")
    'Windows Terminal' = (Test-Path $wtDir) -or (Has 'wt')
    'oh-my-posh'       = Has 'oh-my-posh'
}
$skipped = @($tools.Keys | Where-Object { -not $tools[$_] })

if ($tools['komorebi']) {
    # einmal kopieren: wintheme trägt dort das Farb-Theme ein (das Repo bleibt sauber)
    CopyOnce ".config\komorebi\komorebi.json"     "$env:USERPROFILE\komorebi.json"
    CopyOnce ".config\komorebi\komorebi.bar.json" "$env:USERPROFILE\komorebi.bar.json"
    Link ".config\komorebi\applications.json"   "$env:USERPROFILE\applications.json"
}
if ($tools['whkd']) {
    Link ".config\whkd\whkdrc"                 "$env:USERPROFILE\.config\whkdrc"
}
# Profil für BEIDE PowerShells: Windows PowerShell 5.1 und PowerShell 7 haben getrennte Profile
# (install.ps1 läuft meist unter 5.1, im Terminal oft 7) – prüft selbst, ob oh-my-posh da ist
$docs = [Environment]::GetFolderPath('MyDocuments')
foreach ($dir in 'WindowsPowerShell', 'PowerShell') {
    LinkProfile (Join-Path $docs "$dir\Microsoft.PowerShell_profile.ps1")
}
if ($tools['VS Code']) {
    Link     ".config\vscode\keybindings.json"  "$env:APPDATA\Code\User\keybindings.json"
    CopyOnce ".config\vscode\settings.json"     "$env:APPDATA\Code\User\settings.json"
}
if ($tools['Windows Terminal']) {
    CopyOnce ".config\windows-terminal\settings.json" "$wtDir\LocalState\settings.json"
}

if (Has 'code') {
    Write-Host "`nVS-Code-Erweiterungen …"
    $exts = Get-Content (Join-Path $repo '.config\vscode\extensions.txt') | Where-Object { $_ -match '\S' }
    $codeArgs = $exts | ForEach-Object { '--install-extension', $_ }
    code @codeArgs --force
}

# ── 2. wintheme (Farben aus dem Wallpaper) ───────────────────────────────────
function Find-Python {
    # „python“, sonst „py -3“ (Launcher) – nicht der Store-Platzhalter in WindowsApps
    $candidates = @(
        [pscustomobject]@{ Name = 'python'; Args = [string[]]@() },
        [pscustomobject]@{ Name = 'py';     Args = [string[]]@('-3') }
    )
    foreach ($c in $candidates) {
        $exe = Get-Command $c.Name -CommandType Application -ErrorAction SilentlyContinue | Select-Object -First 1
        if (-not $exe -or $exe.Source -like '*\WindowsApps\python*') { continue }
        $pyArgs = $c.Args
        $ok = & $exe.Source @pyArgs -c 'import sys; print(sys.version_info >= (3, 10))' 2>$null | Select-Object -Last 1
        if ($ok -eq 'True') { return [pscustomobject]@{ Exe = $exe.Source; Args = $pyArgs } }
    }
    return $null
}
$py = Find-Python
if (-not $py) {
    Write-Host "`nPython fehlt – wird für diesen Benutzer installiert (winget) …"
    winget install -e --id Python.Python.3.12 --scope user --accept-package-agreements --accept-source-agreements
    $env:Path = [Environment]::GetEnvironmentVariable('Path', 'User') + ';' + [Environment]::GetEnvironmentVariable('Path', 'Machine')
    $py = Find-Python
    if (-not $py) { throw 'Python nicht gefunden – Terminal neu öffnen und install.ps1 erneut starten.' }
}
Write-Host "`nwintheme einrichten …"
New-Item -ItemType Directory -Force -Path $Dest | Out-Null
Copy-Item -Force (Join-Path $repo 'wintheme\wintheme.py') $Dest
Copy-Item -Force -Recurse (Join-Path $repo 'wintheme\templates') $Dest
if (-not (Test-Path $vpy)) {
    $pyArgs = $py.Args
    & $py.Exe @pyArgs -m venv (Join-Path $Dest 'venv')
}
& $vpy -m pip install --quiet --upgrade pip
& $vpy -m pip install --quiet 'materialyoucolor==3.0.4' 'pillow>=10'
$script = Join-Path $Dest 'wintheme.py'

# Befehl „wintheme“: eigener Ordner, dauerhaft im Benutzer-PATH (+ sofort in diesem Fenster)
New-Item -ItemType Directory -Force -Path $Bin | Out-Null
Set-Content -Encoding ASCII -Path $Shim -Value "@`"$vpy`" `"$script`" %*"
Remove-Item -Force $OldShim -ErrorAction SilentlyContinue
$userPath = [Environment]::GetEnvironmentVariable('Path', 'User')
if (-not (($userPath -split ';') -contains $Bin)) {
    [Environment]::SetEnvironmentVariable('Path', (@($userPath, $Bin) | Where-Object { $_ }) -join ';', 'User')
}
if (-not (($env:Path -split ';') -contains $Bin)) { $env:Path = "$env:Path;$Bin" }

New-Item -Force -Path $MenuKey | Out-Null                                  # Rechtsklick auf Bilder
Set-ItemProperty -Path $MenuKey -Name '(default)' -Value 'Als Hintergrund mit Farben (wintheme)'
New-Item -Force -Path "$MenuKey\command" | Out-Null
Set-ItemProperty -Path "$MenuKey\command" -Name '(default)' -Value "`"$vpyw`" `"$script`" `"%1`""

Stop-Watch
if ($NoWatch) {
    Remove-Item -Force $Startup -ErrorAction SilentlyContinue
} else {
    $lnk = (New-Object -ComObject WScript.Shell).CreateShortcut($Startup)       # Autostart
    $lnk.TargetPath = $vpyw
    $lnk.Arguments = "`"$script`" --watch"
    $lnk.WorkingDirectory = $Dest
    $lnk.Description = 'wintheme: Farben bei Wallpaper-Wechsel anpassen'
    $lnk.Save()
    Start-Process -FilePath $vpyw -ArgumentList "`"$script`" --watch" -WindowStyle Hidden
}

Write-Host "`nEinmal mit dem aktuellen Wallpaper einfärben …"
& $vpy $script
if ($skipped.Count) {
    Write-Host "`nÜbersprungen (nicht installiert): $($skipped -join ', ')"
    Write-Host 'Später nachinstalliert? Einfach install.ps1 erneut ausführen.'
}
Write-Host "`nFertig. Neues PowerShell-Fenster öffnen (Prompt-Farben). Hilfe: wintheme --help"
try { Stop-Transcript | Out-Null } catch {}
