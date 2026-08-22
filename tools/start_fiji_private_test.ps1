param(
    [Parameter(Mandatory = $true)]
    [string]$FijiExecutable,

    [string]$PrivateRoot = "C:\LocalWorkflowData",

    [Parameter(ValueFromRemainingArguments = $true)]
    [string[]]$FijiArgs
)

$ErrorActionPreference = "Stop"

if (-not (Test-Path -LiteralPath $FijiExecutable -PathType Leaf)) {
    throw "Fiji executable not found: $FijiExecutable"
}

$existing = Get-Process -Name "ImageJ-win64" -ErrorAction SilentlyContinue
if ($existing) {
    throw "Privacy test blocked: Fiji/ImageJ is already running. Close it first so the test instance inherits private TEMP/TMP/java.io.tmpdir settings."
}

$privateTemp = Join-Path $PrivateRoot "PrivateTemp"
$windowsTemp = Join-Path $privateTemp "Windows"
$javaTemp = Join-Path $privateTemp "Java"

New-Item -ItemType Directory -Force -Path $windowsTemp | Out-Null
New-Item -ItemType Directory -Force -Path $javaTemp | Out-Null

$previousTemp = $env:TEMP
$previousTmp = $env:TMP
$previousJavaToolOptions = $env:JAVA_TOOL_OPTIONS
$previousPrivateRoot = $env:CAUTIOUS_PRIVATE_DATA_ROOT
$previousPrivateTemp = $env:CAUTIOUS_PRIVATE_TEMP_ROOT

try {
    $env:TEMP = $windowsTemp
    $env:TMP = $windowsTemp
    $env:CAUTIOUS_PRIVATE_DATA_ROOT = $PrivateRoot
    $env:CAUTIOUS_PRIVATE_TEMP_ROOT = $privateTemp

    $javaOption = "-Djava.io.tmpdir=$javaTemp"
    if ([string]::IsNullOrWhiteSpace($previousJavaToolOptions)) {
        $env:JAVA_TOOL_OPTIONS = $javaOption
    }
    else {
        $env:JAVA_TOOL_OPTIONS = "$previousJavaToolOptions $javaOption"
    }

    & $FijiExecutable @FijiArgs
    exit $LASTEXITCODE
}
finally {
    $env:TEMP = $previousTemp
    $env:TMP = $previousTmp
    $env:JAVA_TOOL_OPTIONS = $previousJavaToolOptions
    $env:CAUTIOUS_PRIVATE_DATA_ROOT = $previousPrivateRoot
    $env:CAUTIOUS_PRIVATE_TEMP_ROOT = $previousPrivateTemp
}
