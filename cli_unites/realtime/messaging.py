"""Helpers for persisting and broadcasting realtime messages."""
from __future__ import annotations

import asyncio
import logging
from dataclasses import dataclass
from typing import Any, Dict, Optional

try:
    from supabase import Client
except ImportError:  # pragma: no cover - handled during runtime environment setup
    Client = Any  # type: ignore

from .client import SupabaseRealtimeClient

LOGGER = logging.getLogger(__name__)


@dataclass
class RealtimeMessenger:
    """Coordinate Supabase REST/RPC writes with realtime broadcasts."""

    realtime_client: SupabaseRealtimeClient
    supabase_client: Client
    note_table: str = "notes"
    message_table: str = "messages"

    async def publish_note_update(
        self,
        note_payload: Dict[str, Any],
        *,
        table: Optional[str] = None,
        broadcast_event: str = "note_update",
    ) -> Dict[str, Any]:
        """Upsert note payload via Supabase REST before broadcasting."""
        table_name = table or self.note_table
        data = await self._persist(table_name, note_payload, upsert=True)
        await self._broadcast(broadcast_event, data)
        return data

    async def send_direct_message(
        self,
        message_payload: Dict[str, Any],
        *,
        table: Optional[str] = None,
        broadcast_event: str = "direct_message",
        upsert: bool = False,
    ) -> Dict[str, Any]:
        """Store a direct message payload then broadcast the result."""
        table_name = table or self.message_table
        data = await self._persist(table_name, message_payload, upsert=upsert)
        await self._broadcast(broadcast_event, data)
        return data

    async def store_payload(
        self,
        table: str,
        payload: Dict[str, Any],
        *,
        upsert: bool = False,
    ) -> Dict[str, Any]:
        """Insert or upsert payload without emitting a broadcast event."""
        return await self._persist(table, payload, upsert=upsert)

    async def invoke_rpc(
        self,
        function: str,
        params: Dict[str, Any] | None = None,
        *,
        broadcast_event: str | None = None,
    ) -> Dict[str, Any]:
        """Invoke a Supabase RPC function and optionally broadcast the result."""
        params = params or {}

        def _call() -> Dict[str, Any]:
            response = self.supabase_client.functions.invoke(function, body=params)
            result = getattr(response, "data", response)
            return result or {}

        result = await asyncio.to_thread(_call)
        if broadcast_event:
            await self._broadcast(broadcast_event, result)
        return result

    async def _persist(self, table: str, payload: Dict[str, Any], *, upsert: bool) -> Dict[str, Any]:
        def _call() -> Dict[str, Any]:
            query = self.supabase_client.table(table)
            response = query.upsert(payload).execute() if upsert else query.insert(payload).execute()
            result = getattr(response, "data", response)
            return result[0] if isinstance(result, list) and result else result or payload

        try:
            return await asyncio.to_thread(_call)
        except Exception as exc:  # pragma: no cover - runtime feedback
            LOGGER.exception("Failed to persist payload to %s: %s", table, exc)
            raise

    async def _broadcast(self, event_type: str, data: Dict[str, Any]) -> None:
        payload = {"type": event_type, "data": data}
        await self.realtime_client.send_broadcast(payload)
