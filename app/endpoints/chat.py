from datetime import datetime, timezone
from typing import Annotated

import fastapi
from fastapi import Depends, Request, Form
from fastapi.responses import FileResponse, Response, StreamingResponse
from pathlib import Path
import json

from pydantic_ai.messages import (
    ModelMessage,
    ModelRequest,
    ModelResponse,
    TextPart,
    UserPromptPart,
)
from pydantic_ai.exceptions import UnexpectedModelBehavior

from app.models.ChatModels import ChatMessage
from app.services.chat_database import Database
from app.services.chat_service import create_chat_agent


router = fastapi.APIRouter()

# Initialize agent lazily to avoid import-time issues
_agent = None


def get_agent():
    """Get or create the chat agent."""
    global _agent
    if _agent is None:
        _agent = create_chat_agent()
    return _agent


# Get the static files directory
STATIC_DIR = Path(__file__).parent.parent.parent.parent / "static"


def to_chat_message(m: ModelMessage) -> ChatMessage:
    """Convert a model message to a chat message format."""
    first_part = m.parts[0]
    if isinstance(m, ModelRequest):
        if isinstance(first_part, UserPromptPart):
            assert isinstance(first_part.content, str)
            return {
                "role": "user",
                "timestamp": first_part.timestamp.isoformat(),
                "content": first_part.content,
            }
    elif isinstance(m, ModelResponse):
        if isinstance(first_part, TextPart):
            return {
                "role": "model",
                "timestamp": m.timestamp.isoformat(),
                "content": first_part.content,
            }
    raise UnexpectedModelBehavior(f"Unexpected message type for chat app: {m}")


async def get_chat_db():
    """Dependency to get chat database instance."""
    async with Database.connect() as db:
        yield db


@router.get("/")
async def get_chat_interface() -> FileResponse:
    """Serve the chat interface HTML."""
    return FileResponse(STATIC_DIR / "chat_app.html", media_type="text/html")


@router.get("/chat_app.ts")
async def get_chat_typescript() -> FileResponse:
    """Get the raw typescript code."""
    return FileResponse(STATIC_DIR / "chat_app.ts", media_type="text/plain")


@router.get("/messages")
async def get_chat_messages() -> Response:
    """Get all chat messages."""
    async with Database.connect() as database:
        msgs = await database.get_messages()
        return Response(
            b"\n".join(json.dumps(to_chat_message(m)).encode("utf-8") for m in msgs),
            media_type="text/plain",
        )


@router.post("/messages")
async def post_chat_message(prompt: Annotated[str, Form()]) -> StreamingResponse:
    """Send a chat message and stream the response."""

    async def stream_messages():
        """Streams new line delimited JSON `Message`s to the client."""
        # stream the user prompt so that can be displayed straight away
        yield (
            json.dumps(
                {
                    "role": "user",
                    "timestamp": datetime.now(tz=timezone.utc).isoformat(),
                    "content": prompt,
                }
            ).encode("utf-8")
            + b"\n"
        )

        # Connect to database and get chat history
        async with Database.connect() as database:
            # get the chat history so far to pass as context to the agent
            messages = await database.get_messages()

            # Get the agent instance
            agent = get_agent()

            # run the agent with the user prompt and the chat history
            async with agent.run_stream(prompt, message_history=messages) as result:
                async for text in result.stream(debounce_by=0.01):
                    # text here is a `str` and the frontend wants
                    # JSON encoded ModelResponse, so we create one
                    m = ModelResponse(
                        parts=[TextPart(text)], timestamp=result.timestamp()
                    )
                    yield json.dumps(to_chat_message(m)).encode("utf-8") + b"\n"

            # add new messages to the database
            await database.add_messages(result.new_messages_json())

    return StreamingResponse(stream_messages(), media_type="text/plain")
