from __future__ import annotations

import asyncio
import json
from dataclasses import replace

import click
from rich.pretty import Pretty

from ..core import ConfigManager, console, print_error, print_success
from ..realtime import RealtimeChannelConfig, SupabaseRealtimeClient


@click.group()
def realtime() -> None:
    """Work with Supabase Realtime events."""


def _load_realtime_config(channel_override: str | None) -> tuple[str, str, str, str | None]:
    config = ConfigManager().as_dict()
    project_url = config.get("supabase_url")
    api_key = config.get("supabase_key")
    channel = channel_override or config.get("supabase_realtime_channel")
    realtime_url = config.get("supabase_realtime_url")
    if not project_url or not api_key:
        raise RuntimeError(
            "Supabase credentials missing. Run `notes auth --supabase-url ... --supabase-key ...`."
        )
    if not channel:
        channel = "realtime:public:notes"
    return project_url, api_key, channel, realtime_url


@realtime.command()
@click.option("--channel", help="Realtime channel to join (default from config)")
@click.option(
    "--event",
    "events",
    multiple=True,
    type=click.Choice(["INSERT", "UPDATE", "DELETE", "*"], case_sensitive=False),
    help="Filter events to subscribe to",
)
@click.option("--raw", is_flag=True, help="Print raw JSON payloads instead of formatted output")
def listen(channel: str | None, events: tuple[str, ...], raw: bool) -> None:
    """Stream Supabase realtime change events to the terminal."""

    try:
        project_url, api_key, topic, realtime_url = _load_realtime_config(channel)
    except RuntimeError as exc:
        print_error(str(exc))
        return

    event_list = None
    if events:
        event_list = [event.upper() for event in events]
    channel_config = RealtimeChannelConfig.from_topic(topic, event_list)

    async def _run_listener() -> None:
        async with SupabaseRealtimeClient(
            project_url=project_url,
            api_key=api_key,
            channel=channel_config,
            realtime_url=realtime_url,
        ) as client:
            async for message in client.subscribe_iter():
                if raw:
                    console.print_json(data=message)
                    continue
                filtered = {
                    "topic": message.get("topic"),
                    "event": message.get("event"),
                    "type": message.get("payload", {}).get("type"),
                    "data": message.get("payload"),
                }
                console.print(Pretty(filtered, indent_guides=True))

    try:
        asyncio.run(_run_listener())
    except KeyboardInterrupt:
        print_success("Stopped realtime listener.")
    except Exception as exc:  # pragma: no cover - user feedback
        print_error(f"Realtime listener failed: {exc}")


@realtime.command()
@click.option("--channel", help="Realtime channel to broadcast to (default from config)")
@click.option("--message", help="Plain-text message to broadcast")
@click.option("--payload", help="Raw JSON payload to broadcast")
def send(channel: str | None, message: str | None, payload: str | None) -> None:
    """Broadcast a message to teammates via Supabase Realtime."""

    if not message and not payload:
        raise click.UsageError("Provide either --message or --payload")

    try:
        project_url, api_key, topic, realtime_url = _load_realtime_config(channel)
    except RuntimeError as exc:
        print_error(str(exc))
        return

    try:
        payload_dict = json.loads(payload) if payload else {"type": "message", "content": message}
    except json.JSONDecodeError as err:
        raise click.UsageError(f"Invalid JSON payload: {err}") from err

    channel_config = RealtimeChannelConfig.from_topic(topic)
    channel_config = replace(channel_config, broadcast_ack=True, broadcast_self=True)

    async def _run_sender() -> None:
        async with SupabaseRealtimeClient(
            project_url=project_url,
            api_key=api_key,
            channel=channel_config,
            realtime_url=realtime_url,
        ) as client:
            await client.send_broadcast(payload_dict)

    try:
        asyncio.run(_run_sender())
    except Exception as exc:  # pragma: no cover - user feedback
        print_error(f"Failed to broadcast message: {exc}")
    else:
        print_success("Message broadcast to realtime channel.")
