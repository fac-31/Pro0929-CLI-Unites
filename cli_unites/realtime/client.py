"""Async Supabase Realtime helper built on top of websockets."""
from __future__ import annotations

import asyncio
import contextlib
import json
import logging
from dataclasses import dataclass
from itertools import count
from typing import Any, AsyncIterator, Awaitable, Callable, Dict, Iterable, Optional, Sequence
from urllib.parse import urlparse, urlunparse

from websockets.asyncio.client import connect as websocket_connect
from websockets.exceptions import ConnectionClosed

LOGGER = logging.getLogger(__name__)

RealtimeHandler = Callable[[Dict[str, Any]], Awaitable[None] | None]


@dataclass(frozen=True)
class RealtimeChannelConfig:
    """Configuration describing the realtime topic to join."""

    topic: str
    schema: str = "public"
    table: str = "*"
    events: Sequence[str] = ("INSERT", "UPDATE", "DELETE")
    broadcast_ack: bool = False
    broadcast_self: bool = False

    @classmethod
    def from_topic(cls, topic: str, events: Sequence[str] | None = None) -> "RealtimeChannelConfig":
        """Infer schema/table metadata from a Supabase realtime topic string."""
        parts = topic.split(":")
        schema = "public"
        table = "*"
        if len(parts) >= 3 and parts[0] == "realtime":
            schema = parts[1] or schema
            table = parts[2] or table
        cleaned_events = tuple(events) if events else ("INSERT", "UPDATE", "DELETE")
        return cls(topic=topic, schema=schema, table=table, events=cleaned_events)


class SupabaseRealtimeClient:
    """Manage a Supabase Realtime websocket session."""

    HEARTBEAT_TOPIC = "phoenix"
    HEARTBEAT_EVENT = "heartbeat"

    def __init__(
        self,
        *,
        project_url: str,
        api_key: str,
        channel: RealtimeChannelConfig,
        realtime_url: str | None = None,
        handler: RealtimeHandler | None = None,
        heartbeat_interval: float = 25.0,
    ) -> None:
        self.project_url = project_url
        self.api_key = api_key
        self.channel = channel
        self.realtime_url = realtime_url
        self.handler = handler
        self.heartbeat_interval = heartbeat_interval
        self._ws = None
        self._receiver_task: Optional[asyncio.Task[None]] = None
        self._heartbeat_task: Optional[asyncio.Task[None]] = None
        self._ref_generator = count(1)
        self._queue: asyncio.Queue[Dict[str, Any]] = asyncio.Queue()
        self._closed = asyncio.Event()

    @staticmethod
    def derive_realtime_url(project_url: str) -> str:
        parsed = urlparse(project_url)
        scheme = "wss"
        netloc = parsed.netloc or parsed.path  # support urls without scheme
        base_path = parsed.path if parsed.netloc else ""
        if base_path and not base_path.endswith("/"):
            base_path += "/"
        path = f"{base_path}realtime/v1/websocket"
        return urlunparse((scheme, netloc, path, "", "", ""))

    async def __aenter__(self) -> "SupabaseRealtimeClient":
        await self.connect()
        return self

    async def __aexit__(self, exc_type, exc, tb) -> None:
        await self.close()

    async def connect(self) -> None:
        if self._ws is not None:
            return
        if not self.api_key:
            raise RuntimeError("Supabase API key is required for realtime connections")
        endpoint = self.realtime_url or self.derive_realtime_url(self.project_url)
        endpoint = endpoint.rstrip("/")
        if not endpoint.endswith("websocket"):
            endpoint = f"{endpoint}/websocket"
        query = f"apikey={self.api_key}&vsn=1.0.0"
        uri = f"{endpoint}?{query}"
        LOGGER.debug("Connecting to Supabase Realtime: %s", uri)
        self._ws = await websocket_connect(uri, additional_headers={"apikey": self.api_key})
        await self._join_channel()
        self._receiver_task = asyncio.create_task(self._receiver_loop(), name="realtime-receiver")
        self._heartbeat_task = asyncio.create_task(self._heartbeat_loop(), name="realtime-heartbeat")

    async def listen(self, handler: RealtimeHandler | None = None) -> None:
        if handler is not None:
            self.handler = handler
        if self._ws is None:
            await self.connect()
        while not self._closed.is_set():
            try:
                message = await self._queue.get()
            except asyncio.CancelledError:
                break
            if self.handler is not None:
                result = self.handler(message)
                if asyncio.iscoroutine(result):
                    await result

    async def subscribe_iter(self) -> AsyncIterator[Dict[str, Any]]:
        """Async iterator over realtime messages."""
        if self._ws is None:
            await self.connect()
        while not self._closed.is_set():
            message = await self._queue.get()
            yield message

    async def send_broadcast(self, payload: Dict[str, Any]) -> None:
        """Broadcast a payload to the current channel."""
        await self._send({
            "topic": self.channel.topic,
            "event": "broadcast",
            "payload": payload,
            "ref": self._next_ref(),
        })

    async def close(self) -> None:
        if self._closed.is_set():
            return
        self._closed.set()
        if self._heartbeat_task:
            self._heartbeat_task.cancel()
            with contextlib.suppress(asyncio.CancelledError):
                await self._heartbeat_task
        if self._receiver_task:
            self._receiver_task.cancel()
            with contextlib.suppress(asyncio.CancelledError):
                await self._receiver_task
        if self._ws is not None:
            await self._ws.close()
            self._ws = None

    async def _join_channel(self) -> None:
        assert self._ws is not None
        join_ref = self._next_ref()
        payload = {
            "topic": self.channel.topic,
            "event": "phx_join",
            "payload": {
                "config": {
                    "broadcast": {
                        "ack": self.channel.broadcast_ack,
                        "self": self.channel.broadcast_self,
                    },
                    "presence": {"key": ""},
                    "postgres_changes": self._postgres_changes_config(),
                }
            },
            "ref": join_ref,
        }
        await self._send(payload)
        while True:
            raw = await asyncio.wait_for(self._ws.recv(), timeout=15)
            data = self._decode(raw)
            if data.get("event") == "phx_reply" and data.get("ref") == join_ref:
                status = data.get("payload", {}).get("status")
                if status != "ok":
                    raise RuntimeError(f"Failed to join realtime channel: {data}")
                break
            await self._queue.put(data)

    async def _receiver_loop(self) -> None:
        assert self._ws is not None
        try:
            async for raw in self._ws:
                data = self._decode(raw)
                await self._queue.put(data)
        except ConnectionClosed as exc:
            LOGGER.warning("Supabase realtime connection closed: %s", exc)
        finally:
            await self.close()

    async def _heartbeat_loop(self) -> None:
        try:
            while not self._closed.is_set():
                await asyncio.sleep(self.heartbeat_interval)
                await self._send({
                    "topic": self.HEARTBEAT_TOPIC,
                    "event": self.HEARTBEAT_EVENT,
                    "payload": {},
                    "ref": self._next_ref(),
                })
        except asyncio.CancelledError:
            return
        except Exception as exc:  # pragma: no cover - defensive logging
            LOGGER.exception("Realtime heartbeat failed: %s", exc)

    async def _send(self, message: Dict[str, Any]) -> None:
        assert self._ws is not None
        await self._ws.send(json.dumps(message))

    def _postgres_changes_config(self) -> Iterable[Dict[str, Any]]:
        if self.channel.table == "*":
            return [{"event": "*", "schema": self.channel.schema, "table": "*"}]
        events: Sequence[str] = self.channel.events or ("*",)
        unique_events = sorted(set(event.upper() for event in events))
        return [
            {
                "event": event if event in {"INSERT", "UPDATE", "DELETE"} else "*",
                "schema": self.channel.schema,
                "table": self.channel.table,
            }
            for event in unique_events
        ]

    def _decode(self, raw: str | bytes) -> Dict[str, Any]:
        if isinstance(raw, bytes):
            raw = raw.decode("utf-8")
        try:
            return json.loads(raw)
        except json.JSONDecodeError:  # pragma: no cover - passthrough logging
            LOGGER.debug("Ignoring non-JSON realtime payload: %s", raw)
            return {"raw": raw}

    def _next_ref(self) -> str:
        return str(next(self._ref_generator))
