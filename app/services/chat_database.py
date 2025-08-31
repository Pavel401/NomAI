import os
import json
from pathlib import Path
from dataclasses import dataclass, field
from typing import List, Dict, Any, Optional

from supabase import create_client, Client
from datetime import datetime, timezone
from pydantic_ai.messages import ModelMessage, ModelMessagesTypeAdapter
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
            message_list = ModelMessagesTypeAdapter.validate_json(messages)

            json_str = ModelMessagesTypeAdapter.dump_json(message_list)
            messages_dict = json.loads(json_str)

            base_time = localtime or datetime.now(timezone.utc)

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

    def _clean_messages(self, messages: List[ModelMessage]) -> List[ModelMessage]:
        """Clean up messages to remove orphaned tool calls and tool returns."""
        if not messages:
            return messages

        tool_call_map = {}
        tool_return_map = {}

        for i, msg in enumerate(messages):
            if hasattr(msg, "parts"):
                for part in msg.parts:
                    if (
                        hasattr(part, "tool_call_id")
                        and hasattr(part, "tool_name")
                        and not hasattr(part, "content")
                    ):
                        tool_call_map[part.tool_call_id] = i
                    elif hasattr(part, "tool_call_id") and hasattr(part, "content"):
                        tool_return_map[part.tool_call_id] = i

        valid_tool_calls = set()
        for tool_call_id in tool_call_map:
            if (
                tool_call_id in tool_return_map
                and tool_call_map[tool_call_id] < tool_return_map[tool_call_id]
            ):
                valid_tool_calls.add(tool_call_id)
            else:
                print(f"Removing unpaired tool call with ID: {tool_call_id}")

        cleaned_messages = []
        for i, msg in enumerate(messages):
            if hasattr(msg, "parts") and msg.parts:
                valid_parts = []
                has_valid_content = False

                for part in msg.parts:
                    if not hasattr(part, "tool_call_id"):
                        valid_parts.append(part)
                        has_valid_content = True
                    elif hasattr(part, "tool_name") and not hasattr(part, "content"):
                        if part.tool_call_id in valid_tool_calls:
                            valid_parts.append(part)
                            has_valid_content = True
                        else:
                            print(
                                f"Removing tool call without response: {part.tool_call_id}"
                            )
                    elif hasattr(part, "tool_call_id") and hasattr(part, "content"):
                        if part.tool_call_id in valid_tool_calls:
                            valid_parts.append(part)
                            has_valid_content = True
                        else:
                            print(
                                f"Removing tool return without call: {part.tool_call_id}"
                            )

                if valid_parts and has_valid_content:
                    msg.parts = valid_parts
                    cleaned_messages.append(msg)
            else:
                cleaned_messages.append(msg)

        final_messages = []
        pending_tool_calls = set()

        for msg in cleaned_messages:
            if hasattr(msg, "parts"):
                msg_tool_calls = set()
                msg_tool_returns = set()

                for part in msg.parts:
                    if (
                        hasattr(part, "tool_call_id")
                        and hasattr(part, "tool_name")
                        and not hasattr(part, "content")
                    ):
                        msg_tool_calls.add(part.tool_call_id)
                    elif hasattr(part, "tool_call_id") and hasattr(part, "content"):
                        msg_tool_returns.add(part.tool_call_id)

                if msg_tool_calls:
                    pending_tool_calls.update(msg_tool_calls)
                    final_messages.append(msg)

                elif msg_tool_returns:
                    if msg_tool_returns.issubset(pending_tool_calls):
                        pending_tool_calls -= msg_tool_returns
                        final_messages.append(msg)
                    else:
                        print(
                            f"Skipping tool return message with unmatched calls: {msg_tool_returns - pending_tool_calls}"
                        )
                else:
                    final_messages.append(msg)
            else:
                final_messages.append(msg)

        print(f"Cleaned messages: {len(messages)} -> {len(final_messages)}")
        return final_messages

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

            cleaned_messages = self._clean_messages(messages)
            print(
                f"Retrieved {len(cleaned_messages)} messages, validated to {len(cleaned_messages)} messages for user {user_id}"
            )
            return cleaned_messages
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
