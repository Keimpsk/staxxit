param([string]$Compiler = $env:STAXXIT_CXX, [switch]$Debug, [switch]$TestHeuristics, [string]$OutputName = 'staxxit.exe')
$ErrorActionPreference = 'Stop'
if (-not $Compiler) {
    $portable = Join-Path $PSScriptRoot '..\..\.tools\w64devkit\bin\g++.exe'
    if (Test-Path -LiteralPath $portable) { $Compiler = $portable }
    else { $Compiler = 'g++' }
}
$out = Join-Path $PSScriptRoot 'build'
New-Item -ItemType Directory -Force $out | Out-Null
if ([IO.Path]::GetFileName($OutputName) -ne $OutputName) { throw 'OutputName must be a plain filename' }
$flags = @('-std=c++17', '-pthread', '-Wall', '-Wextra')
if ($Debug) { $flags += @('-O1', '-g', '-D_GLIBCXX_ASSERTIONS') }
else { $flags += @('-O3', '-march=native') }
& $Compiler @flags (Join-Path $PSScriptRoot 'staxxit.cpp') '-o' (Join-Path $out $OutputName)
if ($LASTEXITCODE -ne 0) { throw 'C++ build failed' }
& $Compiler --version | Select-Object -First 1
Get-FileHash -Algorithm SHA256 (Join-Path $out $OutputName)
if ($TestHeuristics) {
    & $Compiler @flags (Join-Path $PSScriptRoot 'tests\heuristics.cpp') '-o' (Join-Path $out 'heuristics.exe')
    if ($LASTEXITCODE -ne 0) { throw 'Heuristic test build failed' }
    & (Join-Path $out 'heuristics.exe')
    if ($LASTEXITCODE -ne 0) { throw 'Heuristic tests failed' }
}
