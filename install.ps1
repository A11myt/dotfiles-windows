<#
  dotfiles-windows installieren (Windows 11, ohne Administratorrechte)

  .\install.ps1                 Configs verlinken/kopieren, wintheme einrichten, einmal einfärben
  .\install.ps1 -NoWatch        ohne Autostart von „wintheme --watch“
  .\install.ps1 -Uninstall      Originalfarben wiederherstellen und wintheme entfernen
  .\install.ps1 -Uninstall -KeepColors   wintheme entfernen, Farben behalten
  (Aufruf: powershell -ExecutionPolicy Bypass -File .\install.ps1)

  Nur für installierte Werkzeuge – fehlende (z. B. komorebi, whkd) werden übersprungen.
  Hardlinks (Änderungen landen direkt im Repo): komorebi, whkd, PowerShell-Profil, VS-Code-Tastenkürzel.
  Einmal kopiert (wintheme trägt dort die Farben ein, das Repo bleibt sauber):
  Windows-Terminal- und VS-Code-settings.json. oh-my-posh-Theme wird von wintheme erzeugt.
#>
param([switch]$NoWatch, [switch]$Uninstall, [switch]$KeepColors)
$ErrorActionPreference = 'Stop'
$repo    = $PSScriptRoot
$Dest    = Join-Path $env:LOCALAPPDATA 'wintheme'
$Shim    = Join-Path $env:LOCALAPPDATA 'Microsoft\WindowsApps\wintheme.cmd'   # liegt im PATH
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
    Remove-Item -Recurse -Force $Dest, $Shim, $Startup -ErrorAction SilentlyContinue
    Remove-Item -Recurse -Force $MenuKey -ErrorAction SilentlyContinue
    Write-Host 'wintheme entfernt (Einstellungen/Stände: %APPDATA%\wintheme). Verlinkte Configs bleiben.'
    return
}

# ── 1. Configs ────────────────────────────────────────────────────────────────
function Link($source, $link) {
    $target = Join-Path $repo $source
    New-Item -ItemType Directory -Force -Path (Split-Path $link) | Out-Null
    if (Test-Path $link) { Remove-Item $link -Force }
    New-Item -ItemType HardLink -Path $link -Target $target | Out-Null
    Write-Host "LINK:  $link"
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
    Link ".config\komorebi\komorebi.json"       "$env:USERPROFILE\komorebi.json"
    Link ".config\komorebi\komorebi.bar.json"   "$env:USERPROFILE\komorebi.bar.json"
    Link ".config\komorebi\applications.json"   "$env:USERPROFILE\applications.json"
}
if ($tools['whkd']) {
    Link ".config\whkd\whkdrc"                 "$env:USERPROFILE\.config\whkdrc"
}
Link ".config\powershell\Microsoft.PowerShell_profile.ps1" $PROFILE   # prüft selbst, ob oh-my-posh da ist
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
    # „py -3“ (Python-Launcher), sonst „python“ – nicht der Store-Platzhalter in WindowsApps
    $candidates = @(
        [pscustomobject]@{ Name = 'py';     Args = [string[]]@('-3') },
        [pscustomobject]@{ Name = 'python'; Args = [string[]]@() }
    )
    foreach ($c in $candidates) {
        $exe = Get-Command $c.Name -CommandType Application -ErrorAction SilentlyContinue | Select-Object -First 1
        if (-not $exe -or $exe.Source -like '*\WindowsApps\python*') { continue }
        $pyArgs = $c.Args
        $ok = & $exe.Source @pyArgs -c 'import sys; print(sys.version_info >= (3, 10))' 2>$null
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

Set-Content -Encoding ASCII -Path $Shim -Value "@`"$vpy`" `"$script`" %*"     # Befehl „wintheme“

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
