from __future__ import annotations as _annotations

import asyncio
from dataclasses import dataclass
import json
from typing import Any, List, Dict
from pathlib import Path

from pydantic_ai.messages import ModelMessage, ModelMessagesTypeAdapter
import logfire


from datetime import datetime
from app.config.chat_config import chat_config
from app.services.supabase_chat_database import SupabaseDBClass


@dataclass
class Database:
    """Database to store chat messages in Supabase."""

    supabase_db: SupabaseDBClass

    @classmethod
    async def connect(cls, file: Path | None = None) -> Database:
        """Create a connection to Supabase"""
        with logfire.span("connect to Supabase"):
            supabase_db = SupabaseDBClass()
            return cls(supabase_db)

    async def add_messages(
        self, user_id: str, messages: bytes, localtime: datetime = None
    ):
        """Add messages to Supabase for a specific user"""

        try:
            # Parse the messages from bytes
            message_list = ModelMessagesTypeAdapter.validate_json(messages)

            # Convert to JSON-serializable format using JSON round-trip
            # This ensures all Pydantic objects are properly serialized
            json_str = ModelMessagesTypeAdapter.dump_json(message_list)
            messages_dict = json.loads(json_str)

            await self.supabase_db.add_messages(user_id, messages_dict, localtime)

        except Exception as e:
            print(f"Error in add_messages: {e}")
            # Don't let database errors crash the streaming response

    async def get_messages(self, user_id: str) -> List[ModelMessage]:
        """Get all messages for a user from Supabase"""
        messages_data = await self.supabase_db.get_messages(user_id)

        print(f"Retrieved {len(messages_data)} messages for user {user_id}")

        messages: List[ModelMessage] = []
        for msg_data in messages_data:
            # Convert back to ModelMessage
            try:
                parsed_messages = ModelMessagesTypeAdapter.validate_python([msg_data])
                if isinstance(parsed_messages, list):
                    messages.extend(parsed_messages)
                else:
                    messages.append(parsed_messages)
            except Exception as e:
                print(f"Error parsing message: {e}")
                continue

        return messages
