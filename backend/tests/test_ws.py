import json
import time

import pytest
from fastapi.testclient import TestClient
from fastapi.websockets import WebSocketDisconnect

from fastapi import FastAPI
from jose import jwt

from app.ws import router as ws_router
from app import config as ws_config


@pytest.fixture
def app():
    app = FastAPI()
    app.include_router(ws_router)
    return app


@pytest.fixture
def client(app):
    return TestClient(app)


SECRET = "dev-secret-key-change-in-production"
ALG = "HS256"


def make_token() -> str:
    return jwt.encode({"sub": "tester"}, SECRET, algorithm=ALG)


def test_invalid_token(client):
    try:
        with client.websocket_connect("/ws/agent?token=bad") as ws:
            with pytest.raises(WebSocketDisconnect):
                ws.receive_text()
    except WebSocketDisconnect as exc:
        assert exc.code == 4401
    else:
        pytest.fail("Expected WebSocketDisconnect")


def test_agent_run_stream(client):
    token = make_token()
    with client.websocket_connect(f"/ws/agent?token={token}") as ws:
        ws.send_text(json.dumps({
            "jsonrpc": "2.0",
            "id": "1",
            "method": "agent.run",
            "params": {"prompt": "hello world"},
        }))
        start = ws.receive_json()
        assert start["result"]["status"] == "started"
        tokens = []
        while True:
            msg = ws.receive_json()
            if msg.get("event", {}).get("type") == "token":
                tokens.append(msg["event"]["text"])
            elif msg.get("result", {}).get("status") == "done":
                break
        assert "hello" in "".join(tokens)


def test_oversized_message(client):
    token = make_token()
    big = "a" * (ws_config.ws_settings.MAX_WS_MSG_BYTES + 10)
    with client.websocket_connect(f"/ws/agent?token={token}") as ws:
        ws.send_text(big)
        msg = ws.receive_json()
        assert msg["error"]["code"] == 4009


def test_rate_limit(client):
    token = make_token()
    with client.websocket_connect(f"/ws/agent?token={token}") as ws:
        for i in range(ws_config.ws_settings.RATE_LIMIT_MSGS + 1):
            ws.send_text(json.dumps({
                "jsonrpc": "2.0",
                "id": str(i),
                "method": "ack",
                "params": {"lastSeq": 0},
            }))
        msg = ws.receive_json()
        assert msg["error"]["code"] == 429


def test_heartbeat_idle_timeout(client, monkeypatch):
    ws_config.ws_settings.HEARTBEAT_INTERVAL = 0.1
    ws_config.ws_settings.IDLE_TIMEOUT_SECONDS = 0.2
    token = make_token()
    with client.websocket_connect(f"/ws/agent?token={token}") as ws:
        time.sleep(1.0)
        with pytest.raises(WebSocketDisconnect):
            while True:
                ws.receive_text()
