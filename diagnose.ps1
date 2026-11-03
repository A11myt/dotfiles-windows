<#
  diagnose.ps1 – sammelt alles zur Fehlersuche in logs\ und lädt es hoch (git commit + push)

  .\diagnose.ps1            Bericht schreiben, committen, pushen
  .\diagnose.ps1 -NoPush    nur schreiben
  (Aufruf: powershell -ExecutionPolicy Bypass -File .\diagnose.ps1)

  Datenschutz: Benutzer-, Rechner-, OneDrive-Firmen- und Wallpaper-Name werden ersetzt, Pfade unter dem
  Benutzerordner als %USERPROFILE%. Keine Umgebungsvariablen außer wintheme-Einträgen im PATH.
#>
param([switch]$NoPush)
$ErrorActionPreference = 'Continue'
$repo   = $PSScriptRoot
$logs   = Join-Path $repo 'logs'
$stamp  = Get-Date -Format 'yyyy-MM-dd_HH-mm-ss'
$file   = Join-Path $logs "diagnose-$stamp.log"
$Dest   = Join-Path $env:LOCALAPPDATA 'wintheme'
$vpy    = Join-Path $Dest 'venv\Scripts\python.exe'
$script = Join-Path $Dest 'wintheme.py'
$out    = New-Object System.Collections.Generic.List[string]
# Python-Ausgaben als UTF-8 lesen (sonst „À“ statt „·“)
[Console]::OutputEncoding = [System.Text.Encoding]::UTF8
$env:PYTHONIOENCODING = 'utf-8'
function Say([string]$t) { $out.Add($t) }
function Section([string]$t) { Say ''; Say "== $t ==" }
function Yes([bool]$b) { if ($b) { 'ja' } else { 'NEIN' } }

Section 'System'
Say "Zeit:       $(Get-Date -Format 'yyyy-MM-dd HH:mm:ss')"
Say "PowerShell: $($PSVersionTable.PSVersion) ($($PSVersionTable.PSEdition))"
Say "Windows:    $([Environment]::OSVersion.VersionString)"
Say "Repo:       $repo  (git $((git -C $repo log --oneline -1) 2>&1))"

Section 'Werkzeuge'
foreach ($c in 'komorebic', 'komorebi', 'whkd', 'code', 'oh-my-posh', 'wt', 'pwsh', 'py', 'python', 'git', 'winget', 'wintheme') {
    $cmd = Get-Command $c -ErrorAction SilentlyContinue | Select-Object -First 1
    Say ('{0,-11} {1}' -f $c, $(if ($cmd) { "$($cmd.CommandType): $($cmd.Source)" } else { 'fehlt' }))
}
Say ('{0,-11} {1}' -f 'Terminal', (Yes (Test-Path "$env:LOCALAPPDATA\Packages\Microsoft.WindowsTerminal_8wekyb3d8bbwe")))

Section 'wintheme-Installation'
Say "venv python:  $(Yes (Test-Path $vpy))"
Say "wintheme.py:  $(Yes (Test-Path $script))"
Say "Befehl (bin): $(Yes (Test-Path (Join-Path $Dest 'bin\wintheme.cmd')))"
Say "alter Befehl: $(Yes (Test-Path "$env:LOCALAPPDATA\Microsoft\WindowsApps\wintheme.cmd"))"
Say "Autostart:    $(Yes (Test-Path (Join-Path ([Environment]::GetFolderPath('Startup')) 'wintheme-watch.lnk')))"
Say "Rechtsklick:  $(Yes (Test-Path 'HKCU:\Software\Classes\SystemFileAssociations\image\shell\wintheme'))"
$watch = Get-Process pythonw -ErrorAction SilentlyContinue | Where-Object { $_.Path -like "$Dest*" }
Say "--watch läuft: $(Yes ([bool]$watch))"
if (Test-Path $vpy) { Say "Python: $((& $vpy --version) 2>&1)"; Say "Pakete: $((& $vpy -m pip list --format=freeze 2>$null | Select-String 'materialyoucolor|pillow') -join ', ')" }

Section 'komorebi'
if (Get-Command komorebic -ErrorAction SilentlyContinue) {
    komorebic state *> $null
    Say "läuft: $(Yes ($LASTEXITCODE -eq 0))"
    Say "Version: $((komorebic --version) 2>&1)"
} else { Say 'nicht installiert' }

Section 'PATH (nur wintheme)'
Say "Benutzer-PATH: $(([Environment]::GetEnvironmentVariable('Path', 'User') -split ';' | Where-Object { $_ -like '*wintheme*' }) -join ' ; ')"
Say "dieses Fenster: $(($env:Path -split ';' | Where-Object { $_ -like '*wintheme*' }) -join ' ; ')"

Section 'PowerShell-Profile'
$docs = [Environment]::GetFolderPath('MyDocuments')
foreach ($dir in 'WindowsPowerShell', 'PowerShell') {
    $p = Join-Path $docs "$dir\Microsoft.PowerShell_profile.ps1"
    if (Test-Path $p) {
        $txt = Get-Content $p -Raw -Encoding UTF8
        $loader = $txt -match "^# dotfiles-windows: l"
        # Ladedatei → das geladene Repo-Profil prüfen
        $real = if ($loader -and $txt -match "\. '([^']+)'") { $Matches[1] } else { $p }
        $hasFn = (Test-Path $real) -and ((Get-Content $real -Raw -Encoding UTF8) -match 'function wintheme')
        Say "$dir`: $(if ($loader) { 'Ladedatei → Repo-Profil' } else { 'eigene Datei' }), wintheme-Funktion=$(Yes $hasFn)"
    } else { Say "$dir`: fehlt" }
}
Say "aktuelles `$PROFILE: $PROFILE"

Section 'Einstellungen (config.json)'
$cfg = Join-Path $env:APPDATA 'wintheme\config.json'
if (Test-Path $cfg) { Get-Content $cfg -Encoding UTF8 | ForEach-Object { Say $_ } } else { Say 'keine' }
$hist = Join-Path $env:APPDATA 'wintheme\history'
Say "gespeicherte Stände: $(if (Test-Path $hist) { (Get-ChildItem $hist -Filter *.json).Count } else { 0 }), Original: $(Yes (Test-Path (Join-Path $env:APPDATA 'wintheme\original.json')))"

Section 'Probelauf (wintheme --dry-run)'
if (Test-Path $vpy) { (& $vpy $script --dry-run 2>&1) | ForEach-Object { Say "$_" } } else { Say 'übersprungen – wintheme nicht installiert' }

Section 'wintheme.log (Ende)'
$wl = Join-Path $env:APPDATA 'wintheme\wintheme.log'
if (Test-Path $wl) { Get-Content $wl -Tail 80 -Encoding UTF8 | ForEach-Object { Say $_ } } else { Say 'keins' }

Section 'install.log (Ende)'
$il = Join-Path $env:LOCALAPPDATA 'wintheme-logs\install.log'
if (Test-Path $il) { Get-Content $il -Tail 150 | ForEach-Object { Say $_ } } else { Say 'keins (install.ps1 noch nicht mit Protokoll gelaufen)' }

# ── schwärzen und schreiben ──
$text = $out -join "`r`n"
$text = $text.Replace($env:USERPROFILE, '%USERPROFILE%')
if ($env:USERNAME)     { $text = $text -replace [regex]::Escape($env:USERNAME), '<user>' }
if ($env:COMPUTERNAME) { $text = $text -replace [regex]::Escape($env:COMPUTERNAME), '<pc>' }
$text = $text -replace 'OneDrive - [^\\/\r\n]+', 'OneDrive - <org>'               # Firmenname im OneDrive-Ordner
$text = $text -replace '(?m)^(\S[^\r\n]*?)\.(png|jpe?g|webp|bmp): Ausgangsfarbe', '<bild>.$2: Ausgangsfarbe'   # Wallpaper-Name
New-Item -ItemType Directory -Force -Path $logs | Out-Null
[System.IO.File]::WriteAllText($file, $text, (New-Object System.Text.UTF8Encoding $true))
Write-Host "Bericht: $file"

if (-not $NoPush) {
    git -C $repo add -- "logs/diagnose-$stamp.log"
    git -C $repo commit -q -m "diagnose $stamp" -- "logs/diagnose-$stamp.log"
    git -C $repo push -q
    if ($LASTEXITCODE -eq 0) { Write-Host 'Hochgeladen.' } else { Write-Host 'Push fehlgeschlagen – bitte selbst: git push' }
}
