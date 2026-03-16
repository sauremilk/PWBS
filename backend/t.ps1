<#
.SYNOPSIS
    PWBS Backend – Test-Runner ohne Terminal-Buffer-Probleme

.DESCRIPTION
    Delegiert die pytest-Ausfuehrung an _pytest_run.py (subprocess.run).
    Dadurch kein PowerShell-2>&1-Stream-Mix, kein Start-Process-Cache-Problem.
    Schreibt vollstaendigen Output nach .test-last.txt; zeigt nur
    Fehler + Zusammenfassung im Terminal.

.PARAMETER Path
    Test-Pfad oder -Datei (default: tests/unit/)

.PARAMETER All
    Alle Tests inkl. Integration (benoetigt laufende DBs)

.PARAMETER Open
    Vollstaendige Ausgabe nach dem Lauf im Editor oeffnen

.PARAMETER Verbose
    Mehr Details: --tb=long statt --tb=short

.EXAMPLE
    .\t.ps1
    .\t.ps1 tests/unit/test_cache.py
    .\t.ps1 -All
    .\t.ps1 -Open
#>
param(
    [string]$Path = "tests/unit/",
    [switch]$All,
    [switch]$Open,
    [switch]$Verbose
)

$ErrorActionPreference = "Continue"

$ScriptDir = if ($PSScriptRoot) { $PSScriptRoot } else { $PWD.Path }
$Python = Join-Path $ScriptDir ".venv\Scripts\python.exe"
$Runner = Join-Path $ScriptDir "_pytest_run.py"
$OutFile = Join-Path $ScriptDir ".test-last.txt"
$TbMode = if ($Verbose) { "long" } else { "short" }
$TestPath = if ($All) { "tests/" } else { $Path }

if (-not (Test-Path $Python)) {
    Write-Host "Virtualenv nicht gefunden: $Python" -ForegroundColor Red
    exit 1
}
if (-not (Test-Path $Runner)) {
    Write-Host "_pytest_run.py nicht gefunden: $Runner" -ForegroundColor Red
    exit 1
}

Write-Host ""
Write-Host "  pytest $TestPath  [--tb=$TbMode]" -ForegroundColor Cyan
Write-Host "  Output  -> $OutFile"              -ForegroundColor DarkGray
Write-Host ""

$Start = Get-Date

# _pytest_run.py laeuft pytest via subprocess.run (kein 2>&1-Problem),
# gibt gefilterte Zusammenfassung nach stdout und schreibt Vollausgabe in $OutFile.
$Summary = & $Python $Runner $TestPath $TbMode $OutFile
$ExitCode = $LASTEXITCODE
$Elapsed = [math]::Round(((Get-Date) - $Start).TotalSeconds, 1)

if ($Summary) {
    foreach ($line in $Summary) {
        if ($line -match "FAILED|Error") {
            Write-Host $line -ForegroundColor Red
        }
        elseif ($line -match "passed") {
            Write-Host $line -ForegroundColor Green
        }
        else {
            Write-Host $line
        }
    }
}
else {
    # Fallback: letzte 3 Zeilen der gespeicherten Ausgabe anzeigen
    if (Test-Path $OutFile) {
        Get-Content $OutFile | Where-Object { $_.Trim() } | Select-Object -Last 3 |
        ForEach-Object { Write-Host $_ -ForegroundColor Yellow }
    }
}

Write-Host ""
Write-Host "  Laufzeit: ${Elapsed}s  |  vollstaendig: $OutFile" -ForegroundColor DarkGray

if ($Open) { code $OutFile }

exit $ExitCode

exit $ExitCode

exit $ExitCode
