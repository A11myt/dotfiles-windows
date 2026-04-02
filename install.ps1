# install.ps1 – kein Admin erforderlich (HardLinks statt SymbolicLinks)
$dotfiles = $PSScriptRoot

# 1. Templates kompilieren
Write-Host "Kompiliere Templates..."
& "$dotfiles\build.ps1"

function Link($source, $link) {
    $target = "$dotfiles\$source"
    $dir = Split-Path $link
    if (-not (Test-Path $dir)) {
        New-Item -ItemType Directory -Path $dir -Force | Out-Null
    }
    if (Test-Path $link) {
        Remove-Item $link -Force
    }
    New-Item -ItemType HardLink -Path $link -Target $target | Out-Null
    Write-Host "LINKED: $link"
}

# komorebi
Link ".config\komorebi\komorebi.json"         "$env:USERPROFILE\komorebi.json"
Link ".config\komorebi\komorebi.bar.json"     "$env:USERPROFILE\komorebi.bar.json"
Link ".config\komorebi\applications.json"     "$env:USERPROFILE\applications.json"

# whkd
Link ".config\whkd\whkdrc"                   "$env:USERPROFILE\.config\whkdrc"

# VSCode
Link ".config\vscode\settings.json"           "$env:APPDATA\Code\User\settings.json"
Link ".config\vscode\keybindings.json"        "$env:APPDATA\Code\User\keybindings.json"

# Oh My Posh
Link ".config\ohmyposh\theme.omp.json"        "$env:USERPROFILE\.config\ohmyposh\theme.omp.json"

# PowerShell
Link ".config\powershell\Microsoft.PowerShell_profile.ps1" $PROFILE

# Windows Terminal
Link ".config\windows-terminal\settings.json" `
    "$env:LOCALAPPDATA\Packages\Microsoft.WindowsTerminal_8wekyb3d8bbwe\LocalState\settings.json"

# 2. VSCode Extensions installieren
if (Get-Command code -ErrorAction SilentlyContinue) {
    Write-Host "`nInstalliere VSCode Extensions..."
    $extensions = Get-Content "$dotfiles\.config\vscode\extensions.txt" | Where-Object { $_ -match '\S' }
    $args = $extensions | ForEach-Object { "--install-extension", $_ }
    code @args --force
} else {
    Write-Host "`nVSCode (code) nicht im PATH gefunden – Extensions uebersprungen."
}

Write-Host "`nFertig."
