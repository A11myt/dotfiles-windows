# ── Prompt ────────────────────────────────────────────────────────────────────
if (Get-Command oh-my-posh -ErrorAction SilentlyContinue) {
    oh-my-posh init pwsh --config "$env:USERPROFILE\.config\ohmyposh\theme.omp.json" | Invoke-Expression
}

# ── PSReadLine ────────────────────────────────────────────────────────────────
Set-PSReadLineOption -EditMode Windows
Set-PSReadLineOption -PredictionSource HistoryAndPlugin
Set-PSReadLineOption -PredictionViewStyle ListView
Set-PSReadLineOption -HistorySearchCursorMovesToEnd
Set-PSReadLineKeyHandler -Key UpArrow   -Function HistorySearchBackward
Set-PSReadLineKeyHandler -Key DownArrow -Function HistorySearchForward
Set-PSReadLineKeyHandler -Chord "Ctrl+f" -Function ForwardWord

# ── Terminal-Icons ─────────────────────────────────────────────────────────────
if (Get-Module -ListAvailable Terminal-Icons) {
    Import-Module Terminal-Icons
}

# ── Aliases ───────────────────────────────────────────────────────────────────
Set-Alias ll    ls
Set-Alias g     git
Set-Alias grep  findstr
Set-Alias touch New-Item
Set-Alias mvdir Move-Item
Set-Alias ws    Set-WorkspaceLocation
Set-Alias gd    Get-DllVersions

# ── Workspace navigation ──────────────────────────────────────────────────────
$WorkspaceMap = @{
    Repos = "C:\Workspace\Repositories"
    Dep   = "C:\Workspace\Deployment"
    Git   = "C:\Workspace\Git"
    Local = "C:\Workspace\Local"
}

function Set-WorkspaceLocation {
    param(
        [ValidateSet('Repos','Dep','Git','Local')]
        [string]$name
    )
    Set-Location $WorkspaceMap[$name]
}

# ── DLL version helper ────────────────────────────────────────────────────────
function Get-DllVersions([string]$path = ".") {
    Get-ChildItem -Path $path -Filter *.dll | ForEach-Object {
        $v = [System.Diagnostics.FileVersionInfo]::GetVersionInfo($_.FullName)
        [PSCustomObject]@{ File = $_.Name; Version = $v.FileVersion }
    }
}

