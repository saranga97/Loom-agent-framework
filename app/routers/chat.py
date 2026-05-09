# Loom AI - Agent Framework | SSE Streaming Chat Router

import json
from fastapi import APIRouter, HTTPException, WebSocket, WebSocketDisconnect
from sse_starlette.sse import EventSourceResponse
from langchain_core.messages import HumanMessage

from app.models.schemas import (
    ChatRequest,
    StartChatRequest,
    StartChatResponse,
    ChatRoomListResponse,
    ChatRoomSummary,
    ChatHistoryResponse,
    ChatMessage,
)
from app.services import tenant as tenant_service
from app.services import chat_history
from app.graph.builder import build_agent_graph
from app.llm.factory import get_llm

router = APIRouter(prefix="/api/v1/chat", tags=["Chat"])


@router.post("/{tenant_name}/start", response_model=StartChatResponse)
async def start_chat(tenant_name: str, body: StartChatRequest):
    """Create a new chat room and return a greeting."""
    config = await tenant_service.get_tenant(tenant_name)
    if config is None:
        raise HTTPException(status_code=404, detail=f"Tenant '{tenant_name}' not found")

    room_id = await chat_history.create_room(tenant_name, body.username)

    chatbot_name = config.chatbot_name
    llm = get_llm(config.response_llm_provider, config.response_model)
    greeting_response = await llm.ainvoke([
        {"role": "system", "content": (
            f"You are {chatbot_name}. {config.agent_instructions}\n"
            f"Generate a short, friendly greeting for a user named {body.username} "
            f"who just opened the chat. Be warm and natural — vary your tone and wording. "
            f"1-2 sentences max. Do not use markdown."
        )},
        {"role": "user", "content": "Say hello and offer to help."},
    ])
    greeting = greeting_response.content

    await chat_history.save_message(tenant_name, room_id, "assistant", greeting)

    return StartChatResponse(room_id=room_id, username=body.username, greeting=greeting)


@router.get("/{tenant_name}/rooms", response_model=ChatRoomListResponse)
async def list_rooms(tenant_name: str):
    """List all chat rooms for a tenant."""
    config = await tenant_service.get_tenant(tenant_name)
    if config is None:
        raise HTTPException(status_code=404, detail=f"Tenant '{tenant_name}' not found")

    rooms = await chat_history.list_rooms(tenant_name)
    summaries = [
        ChatRoomSummary(
            room_id=r["room_id"],
            username=r["username"],
            created_at=r["created_at"],
            updated_at=r.get("updated_at"),
            message_count=r.get("message_count", 0),
        )
        for r in rooms
    ]
    return ChatRoomListResponse(rooms=summaries, total=len(summaries))


@router.get("/{tenant_name}/{room_id}/history", response_model=ChatHistoryResponse)
async def get_history(tenant_name: str, room_id: str):
    """Get full chat history for a room."""
    room = await chat_history.get_history(tenant_name, room_id)
    if room is None:
        raise HTTPException(status_code=404, detail=f"Room '{room_id}' not found")

    messages = [
        ChatMessage(role=m["role"], content=m["content"], timestamp=m.get("timestamp"))
        for m in room.get("messages", [])
    ]
    return ChatHistoryResponse(room_id=room_id, username=room["username"], messages=messages)


@router.post("/{tenant_name}/{room_id}")
async def chat(tenant_name: str, room_id: str, body: ChatRequest):
    """SSE streaming chat — emits token, tool_call, tool_result, done, error events."""
    config = await tenant_service.get_tenant(tenant_name)
    if config is None:
        raise HTTPException(status_code=404, detail=f"Tenant '{tenant_name}' not found")

    # Load room from MongoDB
    room = await chat_history.get_history(tenant_name, room_id)
    if room is None:
        raise HTTPException(status_code=404, detail=f"Room '{room_id}' not found")

    username = room["username"]

    # Inject username into agent instructions
    config_dict = config.model_dump()
    config_dict["agent_instructions"] = (
        config_dict["agent_instructions"]
        + f"\nThe user's name is {username}. Address them by name naturally."
    )

    agent_graph = build_agent_graph(config_dict)

    # Build chat summary from MongoDB history
    history_lines = []
    for msg in room.get("messages", []):
        role = msg.get("role", "")
        content = msg.get("content", "")
        if role == "user":
            history_lines.append(f"User: {content}")
        elif role == "assistant":
            history_lines.append(f"Assistant: {content}")

    chat_summary = ""
    if history_lines:
        chat_summary = "Previous conversation:\n" + "\n".join(history_lines)

    # Save user message to MongoDB
    await chat_history.save_message(tenant_name, room_id, "user", body.message)

    initial_state = {
        "messages": [HumanMessage(content=body.message)],
        "tenant_name": tenant_name,
        "tenant_config": config_dict,
        "chat_summary": chat_summary,
    }

    async def event_generator():
        full_response = ""
        try:
            async for event in agent_graph.astream_events(initial_state, version="v2"):
                kind = event.get("event", "")
                metadata = event.get("metadata", {})
                node = metadata.get("langgraph_node", "")

                # Stream tokens from response node only
                if kind == "on_chat_model_stream" and node == "response":
                    chunk = event.get("data", {}).get("chunk")
                    if chunk and hasattr(chunk, "content") and chunk.content:
                        full_response += chunk.content
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

            # Save assistant response to MongoDB
            if full_response:
                await chat_history.save_message(tenant_name, room_id, "assistant", full_response)

            yield {"event": "done", "data": json.dumps({"status": "complete"})}

        except Exception as e:
            yield {"event": "error", "data": json.dumps({"error": str(e)})}

    return EventSourceResponse(event_generator())


@router.websocket("/{tenant_name}/{room_id}/ws")
async def chat_ws(websocket: WebSocket, tenant_name: str, room_id: str):
    """WebSocket streaming chat — mirrors SSE event protocol."""
    config = await tenant_service.get_tenant(tenant_name)
    if config is None:
        await websocket.close(code=4004, reason=f"Tenant '{tenant_name}' not found")
        return

    room = await chat_history.get_history(tenant_name, room_id)
    if room is None:
        await websocket.close(code=4004, reason=f"Room '{room_id}' not found")
        return

    await websocket.accept()

    username = room["username"]

    try:
        while True:
            data = await websocket.receive_json()
            message = data.get("content", "")
            if not message:
                continue

            # Reload history each turn for up-to-date context
            room = await chat_history.get_history(tenant_name, room_id)

            config_dict = config.model_dump()
            config_dict["agent_instructions"] = (
                config_dict["agent_instructions"]
                + f"\nThe user's name is {username}. Address them by name naturally."
            )

            agent_graph = build_agent_graph(config_dict)

            history_lines = []
            for msg in room.get("messages", []):
                role = msg.get("role", "")
                content = msg.get("content", "")
                if role == "user":
                    history_lines.append(f"User: {content}")
                elif role == "assistant":
                    history_lines.append(f"Assistant: {content}")

            chat_summary = ""
            if history_lines:
                chat_summary = "Previous conversation:\n" + "\n".join(history_lines)

            await chat_history.save_message(tenant_name, room_id, "user", message)

            initial_state = {
                "messages": [HumanMessage(content=message)],
                "tenant_name": tenant_name,
                "tenant_config": config_dict,
                "chat_summary": chat_summary,
            }

            full_response = ""
            try:
                async for event in agent_graph.astream_events(initial_state, version="v2"):
                    kind = event.get("event", "")
                    metadata = event.get("metadata", {})
                    node = metadata.get("langgraph_node", "")

                    if kind == "on_chat_model_stream" and node == "response":
                        chunk = event.get("data", {}).get("chunk")
                        if chunk and hasattr(chunk, "content") and chunk.content:
                            full_response += chunk.content
                            await websocket.send_json({
                                "event": "token",
                                "data": {"content": chunk.content},
                            })

                    elif kind == "on_tool_start":
                        tool_input = event.get("data", {}).get("input", {})
                        await websocket.send_json({
                            "event": "tool_call",
                            "data": {
                                "tool": event.get("name", ""),
                                "input": tool_input if isinstance(tool_input, dict) else {"query": str(tool_input)},
                            },
                        })

                    elif kind == "on_tool_end":
                        output = event.get("data", {}).get("output", "")
                        if hasattr(output, "content"):
                            output = output.content
                        await websocket.send_json({
                            "event": "tool_result",
                            "data": {
                                "tool": event.get("name", ""),
                                "result": str(output)[:500],
                            },
                        })

                if full_response:
                    await chat_history.save_message(tenant_name, room_id, "assistant", full_response)

                await websocket.send_json({"event": "done", "data": {"status": "complete"}})

            except Exception as e:
                await websocket.send_json({"event": "error", "data": {"error": str(e)}})

    except WebSocketDisconnect:
        pass
