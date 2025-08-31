import os
import json
from pathlib import Path
from dataclasses import dataclass, field
from typing import List, Dict, Any, Optional

from supabase import create_client, Client
from datetime import datetime, timezone
from pydantic_ai.messages import (
    ModelMessage,
    ModelMessagesTypeAdapter,
    ModelRequest,
    ModelResponse,
    ToolCallPart,
    ToolReturnPart,
)
import logfire


@dataclass
class Database:
    """
    Database class to store and retrieve chat messages using Supabase.
    """

    supabase_url: str = field(default_factory=lambda: os.getenv("SUPABASE_URL"))
    supabase_key: str = field(default_factory=lambda: os.getenv("SUPABASE_KEY"))
    client: Client = field(init=False)

    def __post_init__(self):
        if not self.supabase_url or not self.supabase_key:
            raise ValueError(
                "Supabase URL and Key must be set in environment variables."
            )
        self.client = create_client(self.supabase_url, self.supabase_key)

    @classmethod
    async def connect(cls, file: Path | None = None) -> "Database":
        """Create a connection to Supabase."""
        with logfire.span("connect to Supabase"):
            return cls()

    async def add_messages(
        self, user_id: str, messages: bytes, localtime: Optional[datetime] = None
    ):
        """
        Add messages to Supabase for a specific user.

        messages: bytes (Pydantic ModelMessages json), e.g.: ModelMessagesTypeAdapter.dump_json(...)
        localtime: optional datetime (client's local time or None)
        """
        try:
            # Parse the messages from bytes (Pydantic)
            message_list = ModelMessagesTypeAdapter.validate_json(messages)
            # Convert to JSON-serializable format
            json_str = ModelMessagesTypeAdapter.dump_json(message_list)
            messages_dict = json.loads(json_str)

            base_time = localtime or datetime.now(timezone.utc)
            # For each message, store with metadata
            messages_to_insert = []
            for msg in messages_dict:
                messages_to_insert.append(
                    {
                        "user_id": user_id,
                        "role": msg.get("role", "user"),
                        "content": msg,
                        "timestamp": base_time.isoformat(),
                    }
                )

            result = (
                self.client.table("chat_messages").insert(messages_to_insert).execute()
            )
            return result
        except Exception as e:
            print(f"Error in add_messages: {e}")
            # Don't let database errors crash the streaming response

    async def get_messages(self, user_id: str) -> List[ModelMessage]:
        """Get all messages for a user from Supabase"""
        try:
            result = (
                self.client.table("chat_messages")
                .select("content")
                .eq("user_id", user_id)
                .order("timestamp", desc=False)
                .execute()
            )

            messages: List[ModelMessage] = []
            for row in result.data:
                msg_data = row["content"]
                try:
                    parsed_messages = ModelMessagesTypeAdapter.validate_python(
                        [msg_data]
                    )
                    if isinstance(parsed_messages, list):
                        messages.extend(parsed_messages)
                    else:
                        messages.append(parsed_messages)
                except Exception as e:
                    print(f"Error parsing message: {e}")
                    continue

            # Fix tool call/tool return message pairs
            validated_messages = self._validate_tool_message_pairs(messages)
            print(
                f"Retrieved {len(messages)} messages, validated to {len(validated_messages)} messages for user {user_id}"
            )
            return validated_messages
        except Exception as e:
            print(f"Error getting messages: {e}")
            raise

    async def get_message_by_id(
        self, user_id: str, message_id: str
    ) -> Optional[ModelMessage]:
        """Get a specific message by ID."""
        try:
            result = (
                self.client.table("chat_messages")
                .select("content")
                .eq("user_id", user_id)
                .eq("id", message_id)
                .single()
                .execute()
            )
            row = result.data
            if row:
                msg_data = row["content"]
                parsed = ModelMessagesTypeAdapter.validate_python([msg_data])
                if isinstance(parsed, list) and parsed:
                    return parsed[0]
                elif isinstance(parsed, ModelMessage):
                    return parsed
            return None
        except Exception as e:
            print(f"Error getting message by ID: {e}")
            return None

    def _validate_tool_message_pairs(
        self, messages: List[ModelMessage]
    ) -> List[ModelMessage]:
        """
        Validate and fix tool call/tool return message pairs to ensure OpenAI compatibility.
        OpenAI requires that messages with role 'tool' must be preceded by messages with 'tool_calls'.
        """
        validated_messages = []
        tool_call_ids = set()

        for i, message in enumerate(messages):
            if isinstance(message, ModelRequest):
                # Check for tool return parts without corresponding tool calls
                has_tool_returns = any(
                    isinstance(part, ToolReturnPart) for part in message.parts
                )

                if has_tool_returns:
                    # Check if there's a corresponding tool call in the previous messages
                    tool_return_ids = {
                        part.tool_call_id
                        for part in message.parts
                        if isinstance(part, ToolReturnPart)
                    }

                    # Only include if all tool return IDs have corresponding tool calls
                    if tool_return_ids.issubset(tool_call_ids):
                        validated_messages.append(message)
                    else:
                        print(
                            f"Skipping message with orphaned tool returns: {tool_return_ids - tool_call_ids}"
                        )
                        continue
                else:
                    # Regular user message or message without tool returns
                    validated_messages.append(message)

            elif isinstance(message, ModelResponse):
                # Check for tool calls and track their IDs
                has_tool_calls = any(
                    isinstance(part, ToolCallPart) for part in message.parts
                )

                if has_tool_calls:
                    # Track tool call IDs for validation of subsequent tool returns
                    for part in message.parts:
                        if isinstance(part, ToolCallPart):
                            tool_call_ids.add(part.tool_call_id)

                validated_messages.append(message)
            else:
                # Other message types
                validated_messages.append(message)

        return validated_messages
