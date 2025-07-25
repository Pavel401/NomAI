from datetime import datetime, timezone
from typing import Annotated, Optional

import fastapi
from fastapi import Depends, Request, Form
from fastapi.responses import FileResponse, Response, StreamingResponse
from pathlib import Path
import json

from pydantic_ai.messages import (
    ModelMessage,
    ModelRequest,
    ModelResponse,
    SystemPromptPart,
    TextPart,
    UserPromptPart,
    ToolCallPart,
    ToolReturnPart,
    FinalResultEvent,
    FunctionToolCallEvent,
    FunctionToolResultEvent,
    PartDeltaEvent,
    PartStartEvent,
    TextPartDelta,
    ToolCallPartDelta,
)
from pydantic_ai.exceptions import UnexpectedModelBehavior
from pydantic_ai import Agent

from app.models.ChatModels import ChatMessage
from app.services.chat_database import Database
from app.services.agent_service import AgentService
from pydantic import BaseModel


router = fastapi.APIRouter()

# Initialize agent lazily to avoid import-time issues
_agent = None


def get_agent():
    """Get or create the chat agent."""
    global _agent
    if _agent is None:
        _agent = AgentService.create_chat_agent()
    return _agent


# Get the static files directory
STATIC_DIR = Path(__file__).parent.parent / "static"


def to_chat_message(m: ModelMessage) -> Optional[ChatMessage]:
    """Convert a model message to a chat message format."""
    if isinstance(m, ModelRequest):
        # Look for UserPromptPart in the message parts (skip SystemPromptPart)
        user_prompt_part_found = any(
            isinstance(part, UserPromptPart) for part in m.parts
        )
        tool_return_parts = [
            part for part in m.parts if isinstance(part, ToolReturnPart)
        ]

        if user_prompt_part_found:
            for part in m.parts:
                if isinstance(part, UserPromptPart):
                    assert isinstance(part.content, str)
                    return {
                        "role": "user",
                        "timestamp": part.timestamp.isoformat(),
                        "content": part.content,
                    }
            return None  # Should not be reached if user_prompt_part_found is true

        if tool_return_parts:
            # This is a request that contains tool returns. We can represent this
            # as a special kind of model message for the frontend to display.
            message = {
                "role": "model",
                "timestamp": tool_return_parts[0].timestamp.isoformat(),
                "content": "",  # No direct text content
                "tool_returns": [],
            }
            for part in tool_return_parts:
                message["tool_returns"].append(
                    {
                        "tool_call_id": part.tool_call_id,
                        "content": part.content,
                        "tool_name": getattr(part, "tool_name", "tool_return"),
                    }
                )
            return message

        # If no UserPromptPart or ToolReturnPart found, skip this message
        return None

    elif isinstance(m, ModelResponse):
        # Handle different types of parts in the response
        content_parts = []
        tool_calls = []
        tool_returns = []

        for part in m.parts:
            if isinstance(part, TextPart):
                content_parts.append(part.content)
            elif isinstance(part, ToolCallPart):
                tool_calls.append(
                    {
                        "tool_name": part.tool_name,
                        "args": part.args,
                        "tool_call_id": part.tool_call_id,
                    }
                )
            elif isinstance(part, ToolReturnPart):
                # Get tool name from the content if available
                tool_name = part.tool_name if hasattr(part, "tool_name") else None
                if not tool_name and hasattr(part, "content"):
                    # Try to extract tool name from context or use generic name
                    tool_name = (
                        "calculate_nutrition_by_food_description"  # Our main tool
                    )

                content = part.content
                if hasattr(content, "model_dump"):
                    content = content.model_dump()

                tool_returns.append(
                    {
                        "tool_call_id": part.tool_call_id,
                        "content": content,
                        "tool_name": tool_name,
                    }
                )

        # Combine all text content
        content = "".join(content_parts)

        # Create the message with tool information
        message = {
            "role": "model",
            "timestamp": m.timestamp.isoformat(),
            "content": content,
        }

        # Add tool information if present
        if tool_calls:
            message["tool_calls"] = tool_calls
        if tool_returns:
            message["tool_returns"] = tool_returns

        return message

    raise UnexpectedModelBehavior(f"Unexpected message type for chat app: {m}")


from datetime import datetime, timezone
from typing import Annotated, Optional

import fastapi
from fastapi import Depends, Request, Form, Query
from fastapi.responses import FileResponse, Response, StreamingResponse
from pathlib import Path
import json

# ... (keep all the existing imports)

from app.services.chat_database import Database
from app.services.agent_service import AgentService

router = fastapi.APIRouter()

# ... (keep existing helper functions like get_agent, to_chat_message)


async def get_chat_db():
    """Dependency to get chat database instance."""
    db = await Database.connect()
    return db


@router.get("/messages")
async def get_chat_messages(
    user_id: Annotated[str, Query(..., description="User ID to get messages for")],
) -> Response:
    """Get all chat messages for a specific user."""
    try:
        database = await get_chat_db()
        msgs = await database.get_messages(user_id)
        chat_messages = [to_chat_message(m) for m in msgs]
        # Filter out None values (system-only messages)
        filtered_messages = [msg for msg in chat_messages if msg is not None]

        return Response(
            b"\n".join(json.dumps(msg).encode("utf-8") for msg in filtered_messages),
            media_type="text/plain",
        )
    except Exception as e:
        print(f"Error in get_chat_messages: {e}")
        return Response(
            json.dumps({"error": str(e)}).encode("utf-8"),
            media_type="application/json",
            status_code=500,
        )


@router.post("/messages")
async def post_chat_message(
    prompt: Annotated[str, Form()],
    user_id: Annotated[str, Form(..., description="User ID")],
    local_time: Annotated[Optional[str], Form()] = None,
) -> StreamingResponse:
    """Send a chat message and stream the response."""

    async def stream_messages():
        """Streams new line delimited JSON `Message`s to the client using node-by-node iteration."""
        # Connect to database and get chat history
        database = await get_chat_db()
        messages = await database.get_messages(user_id)
        agent = get_agent()

        accumulated_text = ""
        tool_calls = []
        tool_returns = []
        base_timestamp = None

        # Use client local_time if provided, else server time
        if local_time:
            try:
                base_timestamp = datetime.fromisoformat(local_time)
                if base_timestamp.tzinfo is None:
                    base_timestamp = base_timestamp.replace(tzinfo=timezone.utc)
            except Exception:
                base_timestamp = datetime.now(timezone.utc)
        else:
            base_timestamp = datetime.now(timezone.utc)

        # Begin node-by-node streaming iteration
        async with agent.iter(prompt, message_history=messages) as run:
            async for node in run:
                if Agent.is_user_prompt_node(node):
                    # User prompt node - send user message
                    user_message = {
                        "role": "user",
                        "timestamp": base_timestamp.isoformat(),
                        "content": prompt,
                    }
                    yield json.dumps(user_message).encode("utf-8") + b"\n"

                elif Agent.is_model_request_node(node):
                    # Model request node - stream partial tokens
                    if base_timestamp is None:
                        base_timestamp = datetime.now(timezone.utc)

                    async with node.stream(run.ctx) as request_stream:
                        async for event in request_stream:
                            if isinstance(event, PartDeltaEvent):
                                if isinstance(event.delta, TextPartDelta):
                                    # Stream text delta
                                    accumulated_text += event.delta.content_delta
                                    partial_message = {
                                        "role": "model",
                                        "timestamp": base_timestamp.isoformat(),
                                        "content": accumulated_text,
                                        "is_partial": True,
                                    }
                                    yield json.dumps(partial_message).encode(
                                        "utf-8"
                                    ) + b"\n"

                            elif isinstance(event, FinalResultEvent):
                                # Final result event - model has finished
                                if accumulated_text and not event.tool_name:
                                    final_message = {
                                        "role": "model",
                                        "timestamp": base_timestamp.isoformat(),
                                        "content": accumulated_text,
                                        "is_final": True,
                                    }
                                    if tool_calls:
                                        final_message["tool_calls"] = tool_calls
                                    if tool_returns:
                                        final_message["tool_returns"] = tool_returns
                                    yield json.dumps(final_message).encode(
                                        "utf-8"
                                    ) + b"\n"

                elif Agent.is_call_tools_node(node):
                    # Call tools node - handle tool calls and results
                    async with node.stream(run.ctx) as handle_stream:
                        async for event in handle_stream:
                            if isinstance(event, FunctionToolCallEvent):
                                # Tool call event
                                tool_call = {
                                    "tool_name": event.part.tool_name,
                                    "args": event.part.args,
                                    "tool_call_id": event.part.tool_call_id,
                                }
                                tool_calls.append(tool_call)

                                # Send tool call message
                                tool_call_message = {
                                    "role": "model",
                                    "timestamp": base_timestamp.isoformat(),
                                    "content": "",
                                    "tool_calls": [tool_call],
                                    "is_tool_call": True,
                                }
                                yield json.dumps(tool_call_message).encode(
                                    "utf-8"
                                ) + b"\n"

                            elif isinstance(event, FunctionToolResultEvent):
                                # Tool result event
                                content = event.result.content
                                if hasattr(content, "model_dump"):
                                    content = content.model_dump()

                                tool_return = {
                                    "tool_call_id": event.tool_call_id,
                                    "content": content,
                                    "tool_name": getattr(
                                        event,
                                        "tool_name",
                                        "calculate_nutrition_by_food_description",
                                    ),
                                }
                                tool_returns.append(tool_return)

                                # Send tool result message
                                tool_result_message = {
                                    "role": "model",
                                    "timestamp": base_timestamp.isoformat(),
                                    "content": "",
                                    "tool_returns": [tool_return],
                                    "is_tool_result": True,
                                }
                                yield json.dumps(tool_result_message).encode(
                                    "utf-8"
                                ) + b"\n"

                elif Agent.is_end_node(node):
                    # End node - agent run is complete
                    if run.result and run.result.output:
                        final_message = {
                            "role": "model",
                            "timestamp": base_timestamp.isoformat(),
                            "content": str(run.result.output),
                            "is_final": True,
                        }
                        if tool_calls:
                            final_message["tool_calls"] = tool_calls
                        if tool_returns:
                            final_message["tool_returns"] = tool_returns
                        yield json.dumps(final_message).encode("utf-8") + b"\n"

        result = run.result
        await database.add_messages(user_id, result.new_messages_json(), base_timestamp)

    return StreamingResponse(stream_messages(), media_type="text/plain")


@router.get("/messages/{message_id}/tools")
async def get_message_tools(
    message_id: str, user_id: Annotated[str, Query(..., description="User ID")]
) -> Response:
    """Get tool information for a specific message."""
    database = await get_chat_db()
    message_data = await database.supabase_db.get_message_by_id(user_id, message_id)

    if not message_data:
        return Response(
            json.dumps({"error": "Message not found"}).encode("utf-8"),
            media_type="application/json",
            status_code=404,
        )

    # Extract tool information from the message data
    tool_info = {"tool_calls": [], "tool_returns": []}

    # Parse the message and extract tool info
    if "tool_calls" in message_data:
        tool_info["tool_calls"] = message_data["tool_calls"]
    if "tool_returns" in message_data:
        tool_info["tool_returns"] = message_data["tool_returns"]

    return Response(
        json.dumps(tool_info).encode("utf-8"), media_type="application/json"
    )


@router.get("/")
async def get_chat_interface() -> FileResponse:
    """Serve the chat interface HTML."""
    return FileResponse(STATIC_DIR / "chat_app.html", media_type="text/html")


@router.get("/chat_app.ts")
async def get_chat_typescript() -> FileResponse:
    """Get the raw typescript code."""
    return FileResponse(STATIC_DIR / "chat_app.ts", media_type="text/plain")
