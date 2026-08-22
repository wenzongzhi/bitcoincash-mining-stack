import json
import time

from fastapi.testclient import TestClient

from app.main import create_app


def test_health_and_dummy_plugin() -> None:
    with TestClient(create_app()) as client:
        health = client.get("/api/health")
        assert health.status_code == 200
        assert health.json() == {"status": "ok"}

        plugins = client.get("/api/plugins")
        assert plugins.status_code == 200
        plugin_ids = [item["plugin_id"] for item in plugins.json()]
        assert "dummy" in plugin_ids
        assert "bch-stratum-proxy" in plugin_ids

        snapshot = client.get("/api/plugins/dummy/snapshot")
        assert snapshot.status_code == 200
        body = snapshot.json()
        assert body["status"]["state"] == "running"
        assert any(item["key"] == "counter" for item in body["metrics"])
        assert body["data"] == {}


def test_action_and_unknown_plugin() -> None:
    with TestClient(create_app()) as client:
        response = client.post("/api/plugins/dummy/actions/reset_counter")
        assert response.status_code == 200
        assert response.json()["success"] is True

        missing = client.get("/api/plugins/no-such-plugin/status")
        assert missing.status_code == 404


def test_websocket_snapshot() -> None:
    with TestClient(create_app()) as client:
        with client.websocket_connect("/api/ws/plugins/dummy") as websocket:
            body = websocket.receive_json()
            assert body["status"]["plugin_id"] == "dummy"
            assert body["status"]["state"] == "running"
            assert isinstance(body["metrics"], list)
            assert body["data"] == {}


def test_bch_stratum_runtime_status_plugin(tmp_path, monkeypatch) -> None:
    status_path = tmp_path / "runtime_status.json"
    now = time.time()
    status_path.write_text(
        json.dumps(
            {
                "schema_version": 1,
                "generated_at": now,
                "service": {
                    "id": "bitcoincash-stratum-proxy",
                    "version": "1.0",
                    "state": "running",
                    "pid": 12345,
                    "started_at": now - 120,
                    "uptime_seconds": 120.0,
                },
                "stratum": {
                    "listen_host": "0.0.0.0",
                    "listen_port": 3333,
                    "max_miners": 20,
                    "default_difficulty": 2048,
                    "connected_miners": 1,
                    "subscribed_miners": 1,
                    "authorized_miners": 1,
                },
                "node": {
                    "rpc_host": "127.0.0.1",
                    "rpc_port": 8332,
                    "gbt_poll_interval_seconds": 20,
                    "gbt_ok": True,
                    "last_gbt_at": now,
                    "last_gbt_error": None,
                },
                "chain": {
                    "network": "mainnet",
                    "tip_height": 999998,
                    "template_height": 999999,
                    "previous_block_hash": "00" * 32,
                    "bits": "180170da",
                    "network_difficulty": 825673821234.5,
                    "template_tx_count": 1842,
                    "current_job_id": "job-1",
                    "last_job_at": now,
                },
                "summary": {
                    "hashrate": {
                        "1m_hs": 4.2e12,
                        "5m_hs": 4.1e12,
                        "15m_hs": 4.0e12,
                    },
                    "best_difficulty": 15382932.44,
                    "shares_submitted_total": 100,
                    "shares_accepted_total": 99,
                    "shares_rejected_total": 1,
                    "block_candidates_total": 0,
                    "blocks_accepted_total": 0,
                },
                "miners": [
                    {
                        "connection_id": "192.168.2.101:53122",
                        "remote_ip": "192.168.2.101",
                        "remote_port": 53122,
                        "connected_at": now - 120,
                        "connected_seconds": 120.0,
                        "subscribed": True,
                        "authorized": True,
                        "worker_name": "bitaxe-01",
                        "payout_address": "bitcoincash:qtest",
                        "difficulty": 2048,
                        "current_job_id": "job-1",
                        "last_submit_at": now,
                        "last_accepted_at": now,
                        "last_rejected_at": None,
                        "shares": {
                            "submitted": 100,
                            "accepted": 99,
                            "rejected": 1,
                            "rejected_by_reason": {"stale": 1},
                        },
                        "last_share_difficulty": 12000,
                        "best_difficulty": 15382932.44,
                        "hashrate": {
                            "1m_hs": 4.2e12,
                            "5m_hs": 4.1e12,
                            "15m_hs": 4.0e12,
                        },
                        "block_candidates": 0,
                        "blocks_accepted": 0,
                    }
                ],
            }
        ),
        encoding="utf-8",
    )

    monkeypatch.setenv("BCH_RUNTIME_STATUS_FILE", str(status_path))

    with TestClient(create_app()) as client:
        snapshot = client.get("/api/plugins/bch-stratum-proxy/snapshot")
        assert snapshot.status_code == 200
        body = snapshot.json()
        assert body["status"]["state"] == "running"
        assert body["status"]["pid"] == 12345
        assert body["data"]["runtime"]["miners"][0]["worker_name"] == "bitaxe-01"
        assert any(item["key"] == "hashrate_5m" for item in body["metrics"])
