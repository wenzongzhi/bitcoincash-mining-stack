@echo off

cd /d "%~dp0"

if not exist "runtime" mkdir "runtime"

set "BCH_RUNTIME_STATUS_FILE=%~dp0runtime\runtime_status.json"
set "DASHBOARD_HOST=0.0.0.0"

start "BCH Stratum Proxy" python ".\bitcoincash-stratum-proxy\bitcoincash_stratum_proxy.py"
start "BCH Dashboard" python ".\python-service-dashboard\run.py"