# Loom AI - Agent Framework | SSE Streaming Chat Router

import json
from fastapi import APIRouter, HTTPException
from sse_starlette.sse import EventSourceResponse
from langchain_core.messages import HumanMessage, AIMessage

from app.models.schemas import ChatRequest
from app.services import tenant as tenant_service
from app.graph.builder import build_agent_graph

router = APIRouter(prefix="/api/v1/chat", tags=["chat"])


@router.post("/{tenant_name}")
async def chat(tenant_name: str, body: ChatRequest):
    """SSE streaming chat — emits token, tool_call, tool_result, done, error events."""
    config = await tenant_service.get_tenant(tenant_name)
    if config is None:
        raise HTTPException(status_code=404, detail=f"Tenant '{tenant_name}' not found")

    config_dict = config.model_dump()
    agent_graph = build_agent_graph(config_dict)

    # Build message history
    messages = []
    for msg in body.conversation_history:
        role = msg.get("role", "")
        content = msg.get("content", "")
        if role == "user":
            messages.append(HumanMessage(content=content))
        elif role == "assistant":
            messages.append(AIMessage(content=content))
    messages.append(HumanMessage(content=body.message))

    initial_state = {
        "messages": messages,
        "tenant_name": tenant_name,
        "tenant_config": config_dict,
    }

    async def event_generator():
        try:
            async for event in agent_graph.astream_events(initial_state, version="v2"):
                kind = event.get("event", "")
                metadata = event.get("metadata", {})
                node = metadata.get("langgraph_node", "")

                # Stream tokens from response node only
                if kind == "on_chat_model_stream" and node == "response":
                    chunk = event.get("data", {}).get("chunk")
                    if chunk and hasattr(chunk, "content") and chunk.content:
                        yield {"event": "token", "data": json.dumps({"content": chunk.content})}

                elif kind == "on_tool_start":
                    tool_input = event.get("data", {}).get("input", {})
                    yield {"event": "tool_call", "data": json.dumps({
                        "tool": event.get("name", ""),
                        "input": tool_input if isinstance(tool_input, dict) else {"query": str(tool_input)},
                    })}

                elif kind == "on_tool_end":
                    output = event.get("data", {}).get("output", "")
                    if hasattr(output, "content"):
                        output = output.content
                    yield {"event": "tool_result", "data": json.dumps({
                        "tool": event.get("name", ""),
                        "result": str(output)[:500],
                    })}

            yield {"event": "done", "data": json.dumps({"status": "complete"})}

        except Exception as e:
            yield {"event": "error", "data": json.dumps({"error": str(e)})}

    return EventSourceResponse(event_generator())
