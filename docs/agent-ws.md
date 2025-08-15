# Agent WebSocket API

Connect to `/ws/agent` using a JWT access token supplied as the WebSocket subprotocol or `?token` query parameter.

## Client Methods

```json
{ "jsonrpc": "2.0", "id": "1", "method": "agent.run", "params": { "prompt": "hi" } }
```

- `agent.run {prompt, sessionId?, options?}` – start an agent session. Server replies `{result:{status:"started",sessionId}}` then streams events.
- `agent.cancel {jobId}` – cancel running job.
- `session.resume {sessionId,lastSeq}` – replay buffered events after reconnect.
- `ack {lastSeq}` – acknowledge streaming events for backpressure.

## Server Events

Each message uses the envelope:

```json
{ "jsonrpc": "2.0", "event": { "type": "token", "seq": 1, "text": "Hello" } }
```

Types: `token`, `status`, `tool_call`, `tool_result`, `cost_update`, `stderr`, `warning`, `heartbeat`.

## Limits

- Max message size: 256&nbsp;KB
- Rate limit: 20 messages / 10&nbsp;s
- Heartbeat every ~25&nbsp;s; idle connections close after 2 missed heartbeats or 120&nbsp;s of silence
- Ack window: 100 sequences

## Reconnect & Resume

Store the returned `sessionId` and latest `seq`. On reconnect send `session.resume` with these values to resume without duplicate tokens.
