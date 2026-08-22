# Py Service Dashboard

A small, plugin-based FastAPI framework for exposing the runtime state of long-running CLI/service programs through a browser.

This is **Phase 1**: the framework is intentionally independent of Bitcoin/Stratum code. The built-in `DummyPlugin` proves the common contract before a real `BitcoinStratumProxyPlugin` is added.

## Architecture

```text
Browser / Phone
      |
 REST + WebSocket
      |
   FastAPI
      |
DashboardService
      |
PluginRegistry
      |
ProgramPlugin interface
      |
  +---+---------------------+-------------------+
  |                         |                   |
DummyPlugin        BitcoinStratumPlugin   Future plugins
```

FastAPI only understands four plugin capabilities:

- `status`
- `metrics`
- `logs`
- `actions`

A plugin can later wrap an embedded Python service, a subprocess/EXE, a local RPC service, or a log/status file.

## Directory layout

```text
py-service-dashboard/
├── app/
│   ├── api/
│   │   └── router.py
│   ├── core/
│   │   ├── config.py
│   │   ├── models.py
│   │   └── registry.py
│   ├── plugins/
│   │   ├── base.py
│   │   ├── builtin.py
│   │   └── dummy/
│   │       └── plugin.py
│   ├── services/
│   │   └── dashboard.py
│   ├── web/static/
│   │   ├── index.html
│   │   ├── app.js
│   │   └── style.css
│   └── main.py
├── tests/
│   └── test_api.py
├── pyproject.toml
├── requirements.txt
└── run.py
```

## Run on Windows

Create and activate a virtual environment:

```powershell
py -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
```

Run locally first:

```powershell
python run.py
```

Open:

```text
http://127.0.0.1:8000
```

API documentation:

```text
http://127.0.0.1:8000/docs
```

## Tailscale access

The default bind address is deliberately `127.0.0.1` so the first run is local-only.

After Tailscale is installed, get the Windows machine's Tailscale IPv4 address:

```powershell
tailscale ip -4
```

Then bind FastAPI specifically to that address instead of exposing it on every network interface:

```powershell
$env:DASHBOARD_HOST="100.x.y.z"
$env:DASHBOARD_PORT="8000"
python run.py
```

From another device in the same tailnet:

```text
http://100.x.y.z:8000
```

You may also bind to `0.0.0.0`, but that exposes the service to other interfaces too, subject to Windows Firewall. Binding to the Tailscale address is the safer default for this use case.

## API

```text
GET  /api/health
GET  /api/plugins
GET  /api/plugins/{plugin_id}/snapshot
GET  /api/plugins/{plugin_id}/status
GET  /api/plugins/{plugin_id}/metrics
GET  /api/plugins/{plugin_id}/logs
GET  /api/plugins/{plugin_id}/actions
POST /api/plugins/{plugin_id}/actions/{action_key}
WS   /api/ws/plugins/{plugin_id}
```

## Plugin contract

Create a class derived from `ProgramPlugin` and implement:

```python
@property
def summary(self) -> PluginSummary: ...

async def get_status(self) -> StatusSnapshot: ...
async def get_metrics(self) -> list[Metric]: ...
async def get_logs(self, limit: int = 100) -> list[LogEntry]: ...
```

Optional capabilities:

```python
async def on_app_startup(self) -> None: ...
async def on_app_shutdown(self) -> None: ...
async def get_actions(self) -> list[ActionSpec]: ...
async def execute_action(self, action_key: str) -> ActionResult: ...
```

Register it in `app/plugins/builtin.py`.

## Run tests

```powershell
pytest -q
```

## Next phase

The next useful step is **not** to redesign the Web UI. It is to add a generic process adapter layer:

```text
ProgramPlugin
    |
    +-- EmbeddedPythonPlugin
    +-- SubprocessPlugin
    +-- RpcPlugin
    +-- FileStatusPlugin
```

Then `BitcoinStratumProxyPlugin` can be implemented first as an embedded Python adapter or subprocess adapter, while keeping every FastAPI endpoint unchanged.
