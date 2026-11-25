param([string]$Python = 'python', [string]$Compiler = '', [int]$Threads = 32, [switch]$SkipBuild)
$ErrorActionPreference = 'Stop'
function RunPython {
    param([Parameter(ValueFromRemainingArguments=$true)][string[]]$PythonArgs)
    & $Python @PythonArgs
    if ($LASTEXITCODE -ne 0) { throw ('Python failed: ' + ($PythonArgs -join ' ')) }
}
Push-Location (Join-Path $PSScriptRoot '..')
try {
    if (-not $SkipBuild) {
        if ($Compiler) { & "$PSScriptRoot\build.ps1" -Compiler $Compiler -TestHeuristics }
        else { & "$PSScriptRoot\build.ps1" -TestHeuristics }
    }
    $engine = Join-Path $PSScriptRoot 'build\staxxit.exe'
    $env:STAXXIT_CPP = $engine
    RunPython @('-m', 'unittest', 'discover', '-s', 'analysis/tests', '-p', 'test_*.py')
    RunPython @('analysis/tests/differential.py', '--cpp', $engine)
    RunPython @('analysis/tests/runner_audit.py', '--cpp', $engine)
    RunPython @('analysis/complexity.py')
    RunPython @('analysis/tree_summary.py', '--self-test')
    RunPython @('analysis/tree_prefix_exact.py', '--depth', '6')
    RunPython @('analysis/benchmark.py', '--games', '30000')
    foreach ($suite in @('baseline', 'matrix')) {
        RunPython @('analysis/run_study.py', '--suite', $suite, '--threads', "$Threads")
    }
    RunPython @('analysis/summarize.py')
    RunPython @('analysis/select_experiments.py', '--matrix-only')
    $selected = Get-Content -LiteralPath "$PSScriptRoot\results\experiment_selection.json" -Raw | ConvertFrom-Json
    $championArgs = @('--champion-a', "$($selected.champions.A)", '--champion-b', "$($selected.champions.B)")
    foreach ($suite in @('phased', 'policies', 'escape', 'early_escape')) {
        RunPython (@('analysis/run_study.py', '--suite', $suite, '--threads', "$Threads") + $championArgs)
    }
    RunPython @('analysis/summarize.py')
    RunPython @('analysis/select_experiments.py')
    $selected = Get-Content -LiteralPath "$PSScriptRoot\results\experiment_selection.json" -Raw | ConvertFrom-Json
    $scheduleArgs = @('--schedule-a', ($selected.schedules.A -join ','), '--schedule-b', ($selected.schedules.B -join ','))
    RunPython (@('analysis/run_study.py', '--suite', 'adaptive', '--games', '100000', '--threads', "$Threads") + $championArgs + $scheduleArgs)
    RunPython @('analysis/run_study.py', '--suite', 'sensitivity', '--games', '100000', '--threads', "$Threads")
    RunPython @('analysis/summarize.py')
    RunPython @('analysis/tree_summary.py')
    RunPython @('analysis/verify_results.py', '--use-current-runner', '--suites', 'baseline', 'matrix', 'phased', 'policies', 'escape', 'adaptive', 'sensitivity', 'early_escape')
} finally { Pop-Location }
