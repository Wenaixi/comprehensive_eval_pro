# Comprehensive Eval Pro - Ultimate Test Suite
# 2026.02.11

$env:PYTHONPATH = ".."
$env:CEP_LOG_LEVEL = "INFO"

Write-Host "====================================================" -ForegroundColor Cyan
Write-Host "   Comprehensive Eval Pro - Ultimate Test Suite" -ForegroundColor Cyan
Write-Host "====================================================" -ForegroundColor Cyan

# 1. Run core flow tests
Write-Host "`n[1/1] Running core integration tests..." -ForegroundColor Yellow
python tests/test_ultimate_flow.py
if ($LASTEXITCODE -ne 0) {
    Write-Host "FAILED: Core integration tests failed!" -ForegroundColor Red
    exit $LASTEXITCODE
}

Write-Host "`n====================================================" -ForegroundColor Green
Write-Host "   SUCCESS: All tests passed! Project is perfect." -ForegroundColor Green
Write-Host "====================================================" -ForegroundColor Green
