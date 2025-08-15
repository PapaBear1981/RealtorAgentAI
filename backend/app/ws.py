"""WebSocket endpoint for real-time agent sessions."""
from __future__ import annotations

import asyncio
import json
import time
import uuid
from collections import deque
from typing import Any, Deque, Dict, Optional, Literal

from fastapi import APIRouter, WebSocket, WebSocketDisconnect
from pydantic import BaseModel, ValidationError

from .auth import decode_jwt
from .agent_runtime import run_agent
from .config import ws_settings

router = APIRouter()


class Session:
    """Holds buffered events for a session."""

    def __init__(self, session_id: str):
        self.session_id = session_id
        self.seq = 0
        self.buffer: Deque[Dict[str, Any]] = deque(maxlen=1000)
        self.agent_task: Optional[asyncio.Task] = None


sessions: Dict[str, Session] = {}


class Connection:
    def __init__(self, websocket: WebSocket):
        self.ws = websocket
        self.send_queue: asyncio.Queue[Dict[str, Any]] = asyncio.Queue()
        self.last_ack = 0
        self.last_recv = time.time()
        self.rate_timestamps: Deque[float] = deque()
        self.session: Optional[Session] = None


class WSMessage(BaseModel):
    jsonrpc: Literal["2.0"]
    id: Optional[str] = None
    method: str
    params: Dict[str, Any] = {}


class AckParams(BaseModel):
    lastSeq: int


class AgentRunParams(BaseModel):
    prompt: str
    sessionId: Optional[str] = None
    options: Optional[Dict[str, Any]] = None


class CancelParams(BaseModel):
    jobId: str


class ResumeParams(BaseModel):
    sessionId: str
    lastSeq: int


async def websocket_handler(websocket: WebSocket):
    token = websocket.headers.get("sec-websocket-protocol") or websocket.query_params.get("token")
    if not token:
        await websocket.close(code=4401)
        return
    try:
        decode_jwt(token)
    except ValueError:
        await websocket.close(code=4401)
        return

    await websocket.accept(subprotocol=token)

    conn = Connection(websocket)

    writer_task = asyncio.create_task(writer(conn))
    heartbeat_task = asyncio.create_task(heartbeat(conn))

    try:
        await reader(conn)
    except WebSocketDisconnect:
        pass
    finally:
        writer_task.cancel()
        heartbeat_task.cancel()
        if conn.session and conn.session.agent_task:
            conn.session.agent_task.cancel()


@router.websocket("/ws/agent")
async def ws_endpoint(websocket: WebSocket):
    await websocket_handler(websocket)


async def reader(conn: Connection):
    ws = conn.ws
    while True:
        message = await ws.receive()
        conn.last_recv = time.time()

        if message["type"] == "websocket.disconnect":
            raise WebSocketDisconnect

        data = message.get("text")
        if data is None:
            continue

        if len(data.encode("utf-8")) > ws_settings.MAX_WS_MSG_BYTES:
            await conn.send_queue.put({
                "jsonrpc": "2.0",
                "error": {"code": 4009, "message": "Message too large"},
            })
            continue

        now = time.time()
        conn.rate_timestamps.append(now)
        while conn.rate_timestamps and now - conn.rate_timestamps[0] > ws_settings.RATE_LIMIT_INTERVAL:
            conn.rate_timestamps.popleft()
        if len(conn.rate_timestamps) > ws_settings.RATE_LIMIT_MSGS:
            await conn.send_queue.put({
                "jsonrpc": "2.0",
                "error": {"code": 429, "message": "Rate limit exceeded"},
            })
            continue

        try:
            msg_dict = json.loads(data)
            envelope = WSMessage.model_validate(msg_dict)
        except (json.JSONDecodeError, ValidationError):
            await conn.send_queue.put({
                "jsonrpc": "2.0",
                "error": {"code": -32600, "message": "Invalid request"},
            })
            continue

        method = envelope.method
        msg_id = envelope.id
        params = envelope.params

        if method == "ack":
            try:
                ack = AckParams.model_validate(params)
            except ValidationError:
                await conn.send_queue.put({
                    "jsonrpc": "2.0",
                    "id": msg_id,
                    "error": {"code": -32602, "message": "Invalid params"},
                })
                continue
            conn.last_ack = max(conn.last_ack, ack.lastSeq)
            continue

        if method == "agent.run":
            try:
                run_p = AgentRunParams.model_validate(params)
            except ValidationError:
                await conn.send_queue.put({
                    "jsonrpc": "2.0",
                    "id": msg_id,
                    "error": {"code": -32602, "message": "Invalid params"},
                })
                continue
            await handle_run(conn, msg_id, run_p)
        elif method == "agent.cancel":
            try:
                cancel_p = CancelParams.model_validate(params)
            except ValidationError:
                await conn.send_queue.put({
                    "jsonrpc": "2.0",
                    "id": msg_id,
                    "error": {"code": -32602, "message": "Invalid params"},
                })
                continue
            await handle_cancel(conn, msg_id, cancel_p)
        elif method == "session.resume":
            try:
                resume_p = ResumeParams.model_validate(params)
            except ValidationError:
                await conn.send_queue.put({
                    "jsonrpc": "2.0",
                    "id": msg_id,
                    "error": {"code": -32602, "message": "Invalid params"},
                })
                continue
            await handle_resume(conn, msg_id, resume_p)
        else:
            await conn.send_queue.put({
                "jsonrpc": "2.0",
                "id": msg_id,
                "error": {"code": -32601, "message": "Unknown method"},
            })


async def writer(conn: Connection):
    ws = conn.ws
    while True:
        msg = await conn.send_queue.get()
        event = msg.get("event")
        if event and conn.session and "seq" in event:
            while event["seq"] - conn.last_ack > ws_settings.ACK_WINDOW:
                await asyncio.sleep(0.1)
        await ws.send_text(json.dumps(msg))


async def heartbeat(conn: Connection):
    ws = conn.ws
    missed = 0
    while True:
        await asyncio.sleep(ws_settings.HEARTBEAT_INTERVAL)
        await conn.send_queue.put({
            "jsonrpc": "2.0",
            "event": {"type": "heartbeat", "ts": time.time()},
        })
        if time.time() - conn.last_recv > ws_settings.HEARTBEAT_INTERVAL * 2:
            missed += 1
        else:
            missed = 0
        if time.time() - conn.last_recv > ws_settings.IDLE_TIMEOUT_SECONDS or missed >= 2:
            await ws.close()
            break


async def handle_run(conn: Connection, msg_id: Optional[str], params: AgentRunParams):
    session_id = params.sessionId or str(uuid.uuid4())
    session = sessions.get(session_id)
    if session is None:
        session = Session(session_id)
        sessions[session_id] = session
    conn.session = session

    await conn.send_queue.put({
        "jsonrpc": "2.0",
        "id": msg_id,
        "result": {"status": "started", "sessionId": session_id},
    })

    async def run():
        async for ev in run_agent(params.model_dump()):
            session.seq += 1
            ev["seq"] = session.seq
            session.buffer.append(ev)
            await conn.send_queue.put({"jsonrpc": "2.0", "event": ev})
        await conn.send_queue.put({"jsonrpc": "2.0", "id": msg_id, "result": {"status": "done"}})

    session.agent_task = asyncio.create_task(run())


async def handle_cancel(conn: Connection, msg_id: Optional[str], params: CancelParams):
    if conn.session and conn.session.agent_task:
        conn.session.agent_task.cancel()
        await conn.send_queue.put({
            "jsonrpc": "2.0",
            "id": msg_id,
            "result": {"status": "cancelled"},
        })


async def handle_resume(conn: Connection, msg_id: Optional[str], params: ResumeParams):
    session_id = params.sessionId
    last_seq = params.lastSeq
    session = sessions.get(session_id)
    if not session:
        await conn.send_queue.put({
            "jsonrpc": "2.0",
            "id": msg_id,
            "error": {"code": 404, "message": "session not found"},
        })
        return
    conn.session = session
    conn.last_ack = last_seq
    for ev in list(session.buffer):
        if ev.get("seq", 0) > last_seq:
            await conn.send_queue.put({"jsonrpc": "2.0", "event": ev})
    await conn.send_queue.put({
        "jsonrpc": "2.0",
        "id": msg_id,
        "result": {"status": "resumed", "sessionId": session_id},
    })
