# build.ps1 – kompiliert Templates mit Farben aus colors/matugen.json
# Aufruf: .\build.ps1  (oder automatisch durch install.ps1)

$root   = $PSScriptRoot
$colors = Get-Content "$root\colors\matugen.json" -Raw | ConvertFrom-Json

function Build-Template {
    param(
        [string]$Src,
        [string]$Dst
    )
    $content = Get-Content $Src -Raw -Encoding UTF8
    foreach ($prop in $colors.PSObject.Properties) {
        $content = $content.Replace("{{$($prop.Name)}}", $prop.Value)
    }
    $dir = Split-Path $Dst
    if (-not (Test-Path $dir)) { New-Item -ItemType Directory -Path $dir -Force | Out-Null }
    [System.IO.File]::WriteAllText($Dst, $content, [System.Text.Encoding]::UTF8)
    Write-Host "BUILT: $Dst"
}

Build-Template "$root\templates\ohmyposh.json"          "$root\.config\ohmyposh\theme.omp.json"
Build-Template "$root\templates\windows-terminal.json"  "$root\.config\windows-terminal\settings.json"

Write-Host "`nBuild fertig."
