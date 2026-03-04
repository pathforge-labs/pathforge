<#
.SYNOPSIS
    PathForge Local CI Gate - mirrors GitHub Actions ci.yml pipeline.

.DESCRIPTION
    Runs quality gates locally before pushing.
    -Fast mode: Lint only (~15s) -- used by pre-push hook. MyPy runs in CI.
    Full mode: Lint + types + tests + build -- mirrors ci.yml exactly.

.PARAMETER Scope
    Which gates to run: 'all' (default), 'api', or 'web'.

.PARAMETER Fast
    Skip tests and builds. Only run lint checks (~15s). MyPy deferred to CI.
    Used by default in pre-push hook. Full tests run in GitHub Actions CI.

.EXAMPLE
    .\scripts\ci-local.ps1                # Full gates (lint + types + tests + build)
    .\scripts\ci-local.ps1 -Fast          # Fast mode (lint only)
    .\scripts\ci-local.ps1 -Scope api     # API gates only
    .\scripts\ci-local.ps1 -Fast -Scope api  # Fast API gates only
#>

param(
    [ValidateSet("all", "api", "web")]
    [string]$Scope = "all",

    [switch]$Fast
)

# ── Configuration ──────────────────────────────────────────────
$ErrorActionPreference = "Continue"
$ROOT = Split-Path -Parent (Split-Path -Parent $MyInvocation.MyCommand.Path)
$API_DIR = Join-Path (Join-Path $ROOT "apps") "api"
$WEB_DIR = Join-Path (Join-Path $ROOT "apps") "web"
$VENV_PYTHON = Join-Path (Join-Path (Join-Path $API_DIR ".venv") "Scripts") "python.exe"

# ── State ──────────────────────────────────────────────────────
$script:results = @()
$totalStart = Get-Date
$script:failed = $false

# ── Helpers ────────────────────────────────────────────────────
function Write-GateResult {
    param([string]$Name, [string]$Status, [string]$Duration, [string]$Detail)
    if ($Status -eq "PASS") {
        Write-Host "  [PASS] " -ForegroundColor Green -NoNewline
    }
    else {
        Write-Host "  [FAIL] " -ForegroundColor Red -NoNewline
    }
    Write-Host "$Name " -NoNewline
    Write-Host "($Duration)" -ForegroundColor DarkGray -NoNewline
    if ($Detail) { Write-Host " - $Detail" -ForegroundColor DarkGray } else { Write-Host "" }
}

function Invoke-Gate {
    param(
        [string]$Name,
        [string]$WorkDir,
        [string]$Command,
        [string[]]$Arguments
    )

    Write-Host ""
    Write-Host ">> $Name" -ForegroundColor Cyan
    $gateStart = Get-Date

    try {
        Push-Location $WorkDir
        $output = & $Command @Arguments 2>&1 | Out-String
        $exitCode = $LASTEXITCODE
        Pop-Location

        $duration = "{0:N1}s" -f ((Get-Date) - $gateStart).TotalSeconds

        if ($exitCode -ne 0) {
            $script:failed = $true
            $script:results += [PSCustomObject]@{
                Name     = $Name
                Status   = "FAIL"
                Duration = $duration
                Detail   = ""
            }
            Write-GateResult -Name $Name -Status "FAIL" -Duration $duration
            Write-Host $output -ForegroundColor Red
            return $false
        }

        # Extract summary detail from output
        $detail = ""
        if ($output -match "(\d+) passed") {
            $detail = "$($Matches[1]) passed"
        }
        if ($output -match "All checks passed") {
            $detail = "0 errors"
        }

        $script:results += [PSCustomObject]@{
            Name     = $Name
            Status   = "PASS"
            Duration = $duration
            Detail   = $detail
        }
        Write-GateResult -Name $Name -Status "PASS" -Duration $duration -Detail $detail
        return $true
    }
    catch {
        Pop-Location -ErrorAction SilentlyContinue
        $duration = "{0:N1}s" -f ((Get-Date) - $gateStart).TotalSeconds
        $script:failed = $true
        $script:results += [PSCustomObject]@{
            Name     = $Name
            Status   = "FAIL"
            Duration = $duration
            Detail   = $_.Exception.Message
        }
        Write-GateResult -Name $Name -Status "FAIL" -Duration $duration
        Write-Host "  $($_.Exception.Message)" -ForegroundColor Red
        return $false
    }
}

# ── Banner ─────────────────────────────────────────────────────
Write-Host ""
Write-Host "==========================================" -ForegroundColor White
Write-Host "  PathForge - Local CI Gate" -ForegroundColor White
if ($Fast) {
    Write-Host "  Mode: FAST (lint only)" -ForegroundColor Magenta
}
else {
    Write-Host "  Mirrors: .github/workflows/ci.yml" -ForegroundColor DarkGray
}
Write-Host "==========================================" -ForegroundColor White
Write-Host "  Scope: $Scope" -ForegroundColor Yellow

# ── API Quality Gates ──────────────────────────────────────────
if ($Scope -eq "all" -or $Scope -eq "api") {
    Write-Host ""
    Write-Host "--- API: Lint & Test ---" -ForegroundColor White

    # Verify venv exists
    if (-not (Test-Path $VENV_PYTHON)) {
        Write-Host "  [FAIL] Python venv not found at: $VENV_PYTHON" -ForegroundColor Red
        Write-Host "  Run: cd apps/api && python -m venv .venv && .venv\Scripts\pip install '.[dev]'" -ForegroundColor Yellow
        exit 1
    }

    # Gate 1: Ruff lint (mirrors: python -m ruff check app/ tests/)
    $pass = Invoke-Gate -Name "Ruff Lint" -WorkDir $API_DIR `
        -Command $VENV_PYTHON `
        -Arguments @("-m", "ruff", "check", "app/", "tests/")

    if (-not $pass) {
        Write-Host "  Tip: Run '.venv\Scripts\python.exe -m ruff check app/ tests/ --fix' to auto-fix" -ForegroundColor Yellow
    }

    # Gate 2: MyPy type check -- blocking in full mode, skipped in fast mode.
    # MyPy runs as a blocking gate in CI (ci.yml). Skipped in fast mode
    # to keep pre-push hook fast (~15s vs ~200s with strict mode).
    if (-not $script:failed -and -not $Fast) {
        Invoke-Gate -Name "MyPy Type Check" -WorkDir $API_DIR `
            -Command $VENV_PYTHON `
            -Arguments @("-m", "mypy", "app/", "--ignore-missing-imports") | Out-Null
    }
    elseif ($Fast) {
        Write-Host ""
        Write-Host ">> MyPy Type Check" -ForegroundColor Cyan
        Write-Host "  [SKIP] " -ForegroundColor Yellow -NoNewline
        Write-Host "MyPy Type Check " -NoNewline
        Write-Host "(CI-only -- runs in GitHub Actions)" -ForegroundColor DarkGray
        $script:results += [PSCustomObject]@{
            Name     = "MyPy Type Check"
            Status   = "SKIP"
            Duration = "0.0s"
            Detail   = "CI-only"
        }
    }

    # Gate 3: Pytest (mirrors: python -m pytest tests/ -v --tb=short -q)
    # Skipped in -Fast mode — tests run in GitHub Actions CI
    if (-not $script:failed -and -not $Fast) {
        $env:ENVIRONMENT = "testing"
        $env:JWT_SECRET = "ci-local-test-secret-minimum-32-characters-long"
        $env:JWT_REFRESH_SECRET = "ci-local-test-refresh-secret-32-chars-min"

        Invoke-Gate -Name "Pytest" -WorkDir $API_DIR `
            -Command $VENV_PYTHON `
            -Arguments @("-m", "pytest", "tests/", "-q", "--tb=short") | Out-Null

        # Clean up test env vars
        Remove-Item Env:\ENVIRONMENT -ErrorAction SilentlyContinue
        Remove-Item Env:\JWT_SECRET -ErrorAction SilentlyContinue
        Remove-Item Env:\JWT_REFRESH_SECRET -ErrorAction SilentlyContinue
    }
    elseif ($Fast -and -not $script:failed) {
        Write-Host ""
        Write-Host ">> Pytest" -ForegroundColor Cyan
        Write-Host "  [SKIP] " -ForegroundColor Yellow -NoNewline
        Write-Host "Pytest " -NoNewline
        Write-Host "(fast mode -- tests run in GitHub Actions CI)" -ForegroundColor DarkGray
        $script:results += [PSCustomObject]@{
            Name     = "Pytest"
            Status   = "SKIP"
            Duration = "0.0s"
            Detail   = "fast mode"
        }
    }
}

# ── Web Quality Gates ──────────────────────────────────────────
if ($Scope -eq "all" -or $Scope -eq "web") {
    Write-Host ""
    Write-Host "--- Web: Lint & Build ---" -ForegroundColor White

    # Gate 4: Next.js lint (mirrors: pnpm lint)
    if (-not $script:failed) {
        Invoke-Gate -Name "Next.js Lint" -WorkDir $WEB_DIR `
            -Command "pnpm" `
            -Arguments @("lint") | Out-Null
    }

    # Gate 5: Next.js build (mirrors: pnpm build)
    # Skipped in -Fast mode — build runs in GitHub Actions CI
    if (-not $script:failed -and -not $Fast) {
        $env:NEXT_TELEMETRY_DISABLED = "1"

        Invoke-Gate -Name "Next.js Build" -WorkDir $WEB_DIR `
            -Command "pnpm" `
            -Arguments @("build") | Out-Null

        Remove-Item Env:\NEXT_TELEMETRY_DISABLED -ErrorAction SilentlyContinue
    }
    elseif ($Fast -and -not $script:failed) {
        Write-Host ""
        Write-Host ">> Next.js Build" -ForegroundColor Cyan
        Write-Host "  [SKIP] " -ForegroundColor Yellow -NoNewline
        Write-Host "Next.js Build " -NoNewline
        Write-Host "(fast mode -- build runs in GitHub Actions CI)" -ForegroundColor DarkGray
        $script:results += [PSCustomObject]@{
            Name     = "Next.js Build"
            Status   = "SKIP"
            Duration = "0.0s"
            Detail   = "fast mode"
        }
    }
}

# ── Summary ────────────────────────────────────────────────────
$totalDuration = "{0:N1}s" -f ((Get-Date) - $totalStart).TotalSeconds

Write-Host ""
Write-Host "--- Summary ---" -ForegroundColor White
Write-Host ""

foreach ($r in $script:results) {
    switch ($r.Status) {
        "PASS" { Write-Host "  [PASS] " -ForegroundColor Green -NoNewline }
        "WARN" { Write-Host "  [WARN] " -ForegroundColor Yellow -NoNewline }
        "SKIP" { Write-Host "  [SKIP] " -ForegroundColor Yellow -NoNewline }
        default { Write-Host "  [FAIL] " -ForegroundColor Red -NoNewline }
    }
    $padding = " " * [Math]::Max(1, 22 - $r.Name.Length)
    Write-Host "$($r.Name)$padding" -NoNewline
    Write-Host "$($r.Duration)" -ForegroundColor DarkGray -NoNewline
    if ($r.Detail) { Write-Host "  ($($r.Detail))" -ForegroundColor DarkGray } else { Write-Host "" }
}

Write-Host ""
if ($script:failed) {
    Write-Host "==========================================" -ForegroundColor Red
    Write-Host "  FAILED - Do NOT push" -ForegroundColor Red
    Write-Host "==========================================" -ForegroundColor Red
    Write-Host "  Total: $totalDuration" -ForegroundColor DarkGray
    exit 1
}
else {
    Write-Host "==========================================" -ForegroundColor Green
    Write-Host "  ALL GATES PASSED - Safe to push" -ForegroundColor Green
    Write-Host "==========================================" -ForegroundColor Green
    Write-Host "  Total: $totalDuration" -ForegroundColor DarkGray
    exit 0
}
