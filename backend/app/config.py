"""Configuration constants for WebSocket sessions."""

class WSSettings:
    MAX_WS_MSG_BYTES = 256 * 1024
    HEARTBEAT_INTERVAL = 25
    IDLE_TIMEOUT_SECONDS = 120
    ACK_WINDOW = 100
    RATE_LIMIT_MSGS = 20
    RATE_LIMIT_INTERVAL = 10

ws_settings = WSSettings()

__all__ = ["ws_settings"]
