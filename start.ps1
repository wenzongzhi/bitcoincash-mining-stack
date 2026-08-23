$Root = $PSScriptRoot

$RuntimeDir = Join-Path $Root "runtime"

if (-not (Test-Path $RuntimeDir)) {
    New-Item -ItemType Directory -Path $RuntimeDir | Out-Null
}

$env:BCH_RUNTIME_STATUS_FILE =
    Join-Path $RuntimeDir "runtime_status.json"

$env:DASHBOARD_HOST = "0.0.0.0"

Start-Process python `
    -ArgumentList "bitcoincash_stratum_proxy.py" `
    -WorkingDirectory (Join-Path $Root "bitcoincash-stratum-proxy")

Start-Process python `
    -ArgumentList "run.py" `
    -WorkingDirectory (Join-Path $Root "python-service-dashboard")