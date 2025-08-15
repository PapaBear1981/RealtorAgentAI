"""Simplified agent runtime used for WebSocket streaming tests."""
from typing import AsyncGenerator, Dict, Any
import asyncio

async def run_agent(params: Dict[str, Any]) -> AsyncGenerator[Dict[str, Any], None]:
    """Simulate running an agent by streaming token events."""
    prompt: str = params.get("prompt", "")
    words = prompt.split()
    for word in words:
        await asyncio.sleep(0)  # allow context switch
        yield {"type": "token", "text": word + " "}
    yield {"type": "status", "phase": "done"}
