<#
.SYNOPSIS
    Gemini Prototype Launcher (PowerShell)
.DESCRIPTION
    Automatically locates Python 3.11 / Miniforge Conda environment (workflow-c or base)
    and executes the specified prototype script or test suite.
.EXAMPLE
    .\docs\gemini\run_gemini_prototype.ps1 docs\gemini\prototypes\v10\test_adapter.py
    .\docs\gemini\run_gemini_prototype.ps1 docs\gemini\prototypes\project_setup_rename\test_setup_rename.py
#>

[CmdletBinding()]
param(
    [Parameter(Position=0, ValueFromRemainingArguments=$true)]
    [string[]]$ScriptArgs
)

function Find-PythonExecutable {
    # 1. Active Conda Prefix
    if ($env:CONDA_PREFIX -and (Test-Path "$env:CONDA_PREFIX\python.exe")) {
        return "$env:CONDA_PREFIX\python.exe"
    }

    # 2. workflow-c environment (Python 3.11)
    $workflowC = "$env:USERPROFILE\.conda\envs\workflow-c\python.exe"
    if (Test-Path $workflowC) {
        return $workflowC
    }

    # 3. Miniforge base environments
    $miniforgeCandidates = @(
        "C:\ProgramData\miniforge3\python.exe",
        "$env:USERPROFILE\miniforge3\python.exe"
    )
    foreach ($cand in $miniforgeCandidates) {
        if (Test-Path $cand) {
            return $cand
        }
    }

    # 4. Standard py launcher or python in PATH
    $pyCmd = Get-Command "py" -ErrorAction SilentlyContinue
    if ($pyCmd) {
        try {
            $null = & py -3.11 -c "import sys" 2>$null
            if ($LASTEXITCODE -eq 0) {
                return "py -3.11"
            }
        } catch {}
    }

    $pythonCmd = Get-Command "python" -ErrorAction SilentlyContinue
    if ($pythonCmd) {
        return $pythonCmd.Source
    }

    return $null
}

$pyExe = Find-PythonExecutable

if (-not $pyExe) {
    Write-Error "No compatible Python executable found in Miniforge / Conda / PATH."
    exit 1
}

if (-not $ScriptArgs -or $ScriptArgs.Count -eq 0) {
    Write-Host "Gemini Prototype Launcher (PowerShell)" -ForegroundColor Cyan
    Write-Host "Selected Python: $pyExe" -ForegroundColor Green
    & $pyExe --version
    Write-Host "`nUsage: .\docs\gemini\run_gemini_prototype.ps1 <script_path> [args...]"
    exit 0
}

$targetScript = $ScriptArgs[0]
$remainingArgs = $ScriptArgs[1..($ScriptArgs.Count - 1)]

if ($pyExe -eq "py -3.11") {
    & py -3.11 $targetScript $remainingArgs
} else {
    & $pyExe $targetScript $remainingArgs
}
exit $LASTEXITCODE
