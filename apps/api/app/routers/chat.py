import json
from collections.abc import AsyncIterator

from fastapi import APIRouter, HTTPException
from fastapi.responses import StreamingResponse
from pydantic import BaseModel, Field

from app.state import state

router = APIRouter()


class ChatRequest(BaseModel):
    message: str = Field(min_length=1)
    session_id: str = Field(min_length=1)


def _sse(event: str, data: dict) -> str:
    return f"event: {event}\ndata: {json.dumps(data, ensure_ascii=False, default=str)}\n\n"


@router.post("/api/chat")
async def chat(req: ChatRequest) -> StreamingResponse:
    agent = state.agent
    if agent is None:
        raise HTTPException(status_code=503, detail="agent not initialized")

    async def event_stream() -> AsyncIterator[str]:
        try:
            async for ev in agent.stream(req.message):
                if ev.kind == "tool_call":
                    yield _sse("tool_call", {
                        "id": ev.tool_call_id,
                        "name": ev.tool_name,
                        "arguments": ev.tool_arguments,
                    })
                elif ev.kind == "tool_result":
                    yield _sse("tool_result", {
                        "id": ev.tool_call_id,
                        "name": ev.tool_name,
                        "result": ev.result,
                    })
                elif ev.kind == "text_delta":
                    yield _sse("text_delta", {"text": ev.text})
                elif ev.kind == "error":
                    yield _sse("error", {"message": ev.message})
                elif ev.kind == "done":
                    yield _sse("done", {"usage": ev.usage})
        except Exception as e:  # noqa: BLE001
            yield _sse("error", {"message": f"internal error: {e}"})

    return StreamingResponse(
        event_stream(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",
        },
    )


@router.get("/api/devices")
async def devices() -> list[dict]:
    iot = state.iot
    if iot is None:
        raise HTTPException(status_code=503, detail="iot not initialized")
    return [d.model_dump() for d in iot.list_devices()]
