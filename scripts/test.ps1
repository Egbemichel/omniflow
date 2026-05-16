$failed = 0

foreach ($svc in @("auth", "task", "workflow")) {
    Write-Host "`n=== Testing $svc ===" -ForegroundColor Cyan
    $env:PYTHONPATH = "services/$svc"
    pytest "services/$svc/tests/" `
        --cov="services/$svc/app" `
        --cov-report=term-missing `
        --cov-fail-under=85 `
        -v
    if ($LASTEXITCODE -ne 0) { $failed++ }
}

$env:PYTHONPATH = ""

if ($failed -gt 0) {
    Write-Host "`n$failed service(s) failed." -ForegroundColor Red
    exit 1
} else {
    Write-Host "`nAll services passed." -ForegroundColor Green
}