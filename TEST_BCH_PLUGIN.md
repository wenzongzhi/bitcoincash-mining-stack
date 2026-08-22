# BCH Stratum Plugin Test

This directory is an overlay for the current `python-service-dashboard` tree.
Copy/merge the files into the same relative paths in your repository.

## 1. Share one runtime_status.json path

The proxy code previously provided uses `BCH_RUNTIME_STATUS_FILE`.
Use the same environment variable for both processes.

PowerShell example:

```powershell
$env:BCH_RUNTIME_STATUS_FILE="C:\BitcoinMining\runtime\runtime_status.json"
```

Start `bitcoincash-stratum-proxy` first and confirm the JSON file updates every second.

Then start the dashboard:

```powershell
python run.py
```

Open:

```text
http://127.0.0.1:8000/?plugin=bch-stratum-proxy
```

The existing dummy plugin still works at:

```text
http://127.0.0.1:8000/?plugin=dummy
```

## 2. Test the API directly

```text
http://127.0.0.1:8000/api/plugins/bch-stratum-proxy/snapshot
http://127.0.0.1:8000/api/plugins/bch-stratum-proxy/status
http://127.0.0.1:8000/api/plugins/bch-stratum-proxy/metrics
```

## 3. Expected failure behavior

- no JSON file -> `stopped`
- invalid JSON/schema -> `error`
- JSON older than 5 seconds -> `unknown`
- fresh JSON + proxy service state `running` -> `running`
- BCHN GBT error does not stop the dashboard adapter; the proxy state can remain `running` while the error is surfaced in the status card

Adjust stale detection if needed:

```powershell
$env:BCH_STRATUM_STALE_SECONDS="8"
```

## 4. Run tests

```powershell
pytest -q
```

## 5. Future combined-repository layout

Recommended layout:

```text
bitcoin-mining-dashboard/
├── bitcoincash-stratum-proxy/
├── python-service-dashboard/
├── runtime/
│   └── runtime_status.json
└── start.bat
```

Both processes should receive the same absolute `BCH_RUNTIME_STATUS_FILE` value from `start.bat`.
