param(
    [string]$Python = 'python',
    [string]$OutputName = 'GenshinDustCalculator'
)
$ErrorActionPreference = 'Stop'
$taskSource = $PSScriptRoot
$taskSpec = Join-Path $taskSource 'calculator.spec'
$taskOutput = Join-Path $taskSource 'dist'
$taskBuild = Join-Path $taskSource 'build'
$taskPreviousName = $env:DUST_EXE_NAME
try {
    $env:DUST_EXE_NAME = $OutputName
    & $Python -m PyInstaller --noconfirm --distpath $taskOutput --workpath $taskBuild $taskSpec
    if ($LASTEXITCODE -ne 0) { throw 'Build failed' }
} finally {
    $env:DUST_EXE_NAME = $taskPreviousName
}
