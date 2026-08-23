# Bitcoin Cash Mining Stack

A lightweight Bitcoin Cash solo mining stack combining a Stratum V1 proxy with a web-based monitoring dashboard.

The project integrates:

- **bitcoincash-stratum-proxy** — connects ASIC miners to a BCHN full node for Bitcoin Cash solo mining.
- **python-service-dashboard** — provides a FastAPI-based web dashboard for monitoring proxy and miner status.

The two components run independently and exchange runtime information through `runtime/runtime_status.json`.

## Architecture

```text
ASIC Miner
    |
    | Stratum V1
    v
bitcoincash-stratum-proxy
    |
    | BCHN JSON-RPC
    v
BCHN Full Node

    +
    |
    | runtime_status.json
    v

python-service-dashboard
    |
    v
Web Browser / Phone
```

## Requirements

- Windows
- Python 3.11 or newer
- A synchronized BCHN full node
- An ASIC miner with Stratum V1 support

Install all Python dependencies from the repository root:

```bash
python -m pip install -r requirements.txt
```

## Configuration

Before starting, configure the BCHN RPC connection and payout address in:

```text
bitcoincash-stratum-proxy/bitcoincash_stratum_proxy.py
```

For example:

```python
RPC_USER = "your_rpc_user"
RPC_PASS = "your_rpc_password"
RPC_HOST = "127.0.0.1"
RPC_PORT = 8332

LISTEN_HOST = "0.0.0.0"
LISTEN_PORT = 3333

DEFAULT_PAYOUT_ADDRESS = "bitcoincash:your_address"
```

Example BCHN configuration:

```ini
server=1
rpcuser=your_rpc_user
rpcpassword=your_rpc_password
rpcallowip=127.0.0.1
```

## Start

Run:

```text
start.bat
```

or:

```powershell
.\start.ps1
```

The launcher starts both:

```text
bitcoincash-stratum-proxy
python-service-dashboard
```

The dashboard listens on port `8000` by default.

Open the **Bitcoin Cash Stratum Proxy dashboard**:

```text
http://127.0.0.1:8000/?plugin=bch-stratum-proxy
```

For another device on the LAN, replace `127.0.0.1` with the IP address of the Windows host:

```text
http://HOST_IP:8000/?plugin=bch-stratum-proxy
```

## Runtime Data

The proxy writes its runtime state to:

```text
runtime/runtime_status.json
```

The dashboard reads the same file and exposes the information through its web interface.

```text
Proxy
  |
  | write
  v
runtime_status.json
  |
  | read
  v
Dashboard
```

The `runtime/` directory contains temporary runtime data and should not be committed to Git.

## ASIC Configuration

Configure the ASIC pool URL to point to the machine running the proxy:

```text
stratum+tcp://PROXY_IP:3333
```

The Stratum username can be the Bitcoin Cash payout address.

## Security

This project is intended for trusted local networks.

- Do not expose BCHN RPC directly to the Internet.
- Do not expose the Stratum proxy directly to the Internet unless appropriate network security is in place.
- Use strong BCHN RPC credentials.
- Restrict BCHN RPC access to trusted hosts.
- Consider Tailscale or another private network solution for remote dashboard access.

## License

Apache License 2.0.