# install.ps1 – als Admin ausführen
$dotfiles = "C:\Workspace\github\dotfiles-windows"

function Link($source, $link) {
    if (Test-Path $link) {
        Write-Host "EXISTS (skip): $link"
        return
    }
    New-Item -ItemType SymbolicLink -Path $link -Target "$dotfiles\$source" -Force
    Write-Host "LINKED: $link"
}

# komorebi
Link ".config\komorebi\komorebi.json"      "$env:USERPROFILE\komorebi.json"
Link ".config\komorebi\komorebi.bar.json"  "$env:USERPROFILE\komorebi.bar.json"
Link ".config\komorebi\applications.json"  "$env:USERPROFILE\applications.json"

# whkd
Link ".config\whkd\whkdrc"                "$env:USERPROFILE\.config\whkdrc"

# VSCode
Link ".config\vscode\settings.json"        "$env:APPDATA\Code\User\settings.json"
Link ".config\vscode\keybindings.json"     "$env:APPDATA\Code\User\keybindings.json"

# Oh My Posh
Link ".config\ohmyposh\theme.omp.json"     "$env:USERPROFILE\.config\ohmyposh\theme.omp.json"

# Windows Terminal
Link ".config\windows-terminal\settings.json" `
    "$env:LOCALAPPDATA\Packages\Microsoft.WindowsTerminal_8wekyb3d8bbwe\LocalState\settings.json"

Write-Host "`nFertig."