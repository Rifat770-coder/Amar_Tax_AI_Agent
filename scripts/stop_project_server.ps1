$ErrorActionPreference = 'Stop'
$taxProjectRoot = [System.IO.Path]::GetFullPath((Join-Path $PSScriptRoot '..')).TrimEnd('\') + '\'
$taxServers = @(Get-CimInstance Win32_Process -Filter "Name='python.exe'" | Where-Object {
    $_.ExecutablePath -and
    $_.ExecutablePath.StartsWith($taxProjectRoot, [System.StringComparison]::OrdinalIgnoreCase) -and
    $_.CommandLine -match '(?i)-m\s+streamlit\s+run\s+' -and
    $_.CommandLine -match '(?i)app\.py(?:"|\s|$)'
})
foreach ($taxServer in $taxServers) {
    if (Get-Process -Id $taxServer.ProcessId -ErrorAction SilentlyContinue) {
        Stop-Process -Id $taxServer.ProcessId -Force -ErrorAction Stop
    }
}
Write-Output "Stopped $($taxServers.Count) Amar Tax server processes."
