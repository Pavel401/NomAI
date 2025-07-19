from dataclasses import dataclass, field
import os
from supabase import create_client, Client
from typing import List, Dict, Any
import json
from datetime import datetime, timezone
from datetime import datetime, timedelta


@dataclass
class SupabaseDBClass:
    supabase_url: str = field(default_factory=lambda: os.getenv("SUPABASE_URL"))
    supabase_key: str = field(default_factory=lambda: os.getenv("SUPABASE_KEY"))
    client: Client = field(init=False)

    def __post_init__(self):
        if not self.supabase_url or not self.supabase_key:
            raise ValueError(
                "Supabase URL and Key must be set in environment variables."
            )
        self.client = create_client(self.supabase_url, self.supabase_key)

    async def add_messages(
        self, user_id: str, messages: List[Dict[str, Any]], localtime: datetime = None
    ):
        """Add multiple messages to Supabase"""
        try:
            messages_to_insert = []
            base_time = localtime or datetime.now(timezone.utc)

            for i, msg in enumerate(messages):
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
            print(f"Error adding messages: {e}")
            raise

    async def get_messages(self, user_id: str) -> List[Dict[str, Any]]:
        """Get all messages for a user from Supabase"""
        try:
            result = (
                self.client.table("chat_messages")
                .select("content")
                .eq("user_id", user_id)
                .order("timestamp", desc=False)
                .execute()
            )

            return [row["content"] for row in result.data]
        except Exception as e:
            print(f"Error getting messages: {e}")
            raise

    async def get_message_by_id(self, user_id: str, message_id: str) -> Dict[str, Any]:
        """Get a specific message by ID"""
        try:
            result = (
                self.client.table("chat_messages")
                .select("content")
                .eq("user_id", user_id)
                .eq("id", message_id)
                .single()
                .execute()
            )
            return result.data["content"] if result.data else None
        except Exception as e:
            print(f"Error getting message by ID: {e}")
            return None
