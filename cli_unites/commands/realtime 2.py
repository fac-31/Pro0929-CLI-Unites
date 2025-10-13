from __future__ import annotations

import asyncio
import json
from dataclasses import replace
from typing import Any, Dict

import click
from rich.pretty import Pretty

from ..core import ConfigManager, console, print_error, print_success
from ..realtime import RealtimeChannelConfig, RealtimeMessenger, SupabaseRealtimeClient

try:
    from supabase import create_client
except ImportError:  # pragma: no cover - ensures graceful CLI help when optional dep missing
    create_client = None  # type: ignore


@click.group()
def realtime() -> None:
    """Work with Supabase Realtime events."""


def _build_supabase_client(project_url: str, api_key: str):
    if create_client is None:  # pragma: no cover - runtime dependency guard
        raise RuntimeError(
            "Supabase Python client is unavailable. Install the optional dependency to persist messages."
        )
    return create_client(project_url, api_key)


def _load_realtime_config(channel_override: str | None) -> Dict[str, Any]:
    config = ConfigManager().as_dict()
    project_url = config.get("supabase_url")
    api_key = config.get("supabase_key")
    channel = channel_override or config.get("supabase_realtime_channel") or "realtime:public:notes"
    realtime_url = config.get("supabase_realtime_url")
    note_table = config.get("supabase_note_table") or "notes"
    message_table = config.get("supabase_message_table") or "messages"
    if not project_url or not api_key:
        raise RuntimeError(
            "Supabase credentials missing. Run `notes auth --supabase-url ... --supabase-key ...`."
        )
    return {
        "project_url": project_url,
        "api_key": api_key,
        "topic": channel,
        "realtime_url": realtime_url,
        "note_table": note_table,
        "message_table": message_table,
    }


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
        config = _load_realtime_config(channel)
    except RuntimeError as exc:
        print_error(str(exc))
        return

    event_list = None
    if events:
        event_list = [event.upper() for event in events]
    channel_config = RealtimeChannelConfig.from_topic(config["topic"], event_list)

    async def _run_listener() -> None:
        async with SupabaseRealtimeClient(
            project_url=config["project_url"],
            api_key=config["api_key"],
            channel=channel_config,
            realtime_url=config["realtime_url"],
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
        config = _load_realtime_config(channel)
    except RuntimeError as exc:
        print_error(str(exc))
        return

    try:
        payload_dict = json.loads(payload) if payload else {"type": "message", "content": message}
    except json.JSONDecodeError as err:
        raise click.UsageError(f"Invalid JSON payload: {err}") from err

    channel_config = RealtimeChannelConfig.from_topic(config["topic"])
    channel_config = replace(channel_config, broadcast_ack=True, broadcast_self=True)

    async def _run_sender() -> None:
        async with SupabaseRealtimeClient(
            project_url=config["project_url"],
            api_key=config["api_key"],
            channel=channel_config,
            realtime_url=config["realtime_url"],
        ) as client:
            await client.send_broadcast(payload_dict)

    try:
        asyncio.run(_run_sender())
    except Exception as exc:  # pragma: no cover - user feedback
        print_error(f"Failed to broadcast message: {exc}")
    else:
        print_success("Message broadcast to realtime channel.")


@realtime.command(name="note-update")
@click.option("--channel", help="Realtime channel override (default from config)")
@click.option("--note-id", help="Identifier of the note to upsert")
@click.option("--title", help="Optional note title override")
@click.option("--body", help="Optional note body override")
@click.option("--tags", help="Comma separated tags for the note")
@click.option("--payload", help="Raw JSON payload to upsert; overrides other fields")
@click.option("--table", help="Supabase table for notes (default from config)")
@click.option("--event", "broadcast_event", default="note_update", help="Event type used in broadcast payload")
def note_update(
    channel: str | None,
    note_id: str | None,
    title: str | None,
    body: str | None,
    tags: str | None,
    payload: str | None,
    table: str | None,
    broadcast_event: str,
) -> None:
    """Persist a note update through Supabase and broadcast the change."""

    try:
        config = _load_realtime_config(channel)
    except RuntimeError as exc:
        print_error(str(exc))
        return

    try:
        supabase_client = _build_supabase_client(config["project_url"], config["api_key"])
    except RuntimeError as exc:
        print_error(str(exc))
        return

    if payload:
        try:
            note_payload = json.loads(payload)
        except json.JSONDecodeError as err:
            raise click.UsageError(f"Invalid JSON payload: {err}") from err
    else:
        if not note_id:
            raise click.UsageError("Provide --note-id or --payload JSON to describe the note update")
        note_payload = {"id": note_id}
        if title:
            note_payload["title"] = title
        if body:
            note_payload["body"] = body
        if tags:
            tag_list = [tag.strip() for tag in tags.split(",") if tag.strip()]
            note_payload["tags"] = tag_list

    channel_config = RealtimeChannelConfig.from_topic(config["topic"])
    channel_config = replace(channel_config, broadcast_ack=True, broadcast_self=True)

    async def _run_note_update() -> Dict[str, Any]:
        async with SupabaseRealtimeClient(
            project_url=config["project_url"],
            api_key=config["api_key"],
            channel=channel_config,
            realtime_url=config["realtime_url"],
        ) as realtime_client:
            messenger = RealtimeMessenger(
                realtime_client,
                supabase_client,
                note_table=config["note_table"],
                message_table=config["message_table"],
            )
            return await messenger.publish_note_update(
                note_payload,
                table=table,
                broadcast_event=broadcast_event,
            )

    try:
        stored = asyncio.run(_run_note_update())
    except Exception as exc:  # pragma: no cover - user feedback
        print_error(f"Note update failed: {exc}")
        return

    console.print(Pretty({"note": stored}, indent_guides=True))
    print_success("Note update persisted and broadcast.")


@realtime.command(name="direct-message")
@click.option("--channel", help="Realtime channel override (default from config)")
@click.option("--sender", help="Identifier for the message sender")
@click.option("--recipient", help="Identifier for the message recipient")
@click.option("--content", help="Message content (ignored when --payload supplied)")
@click.option("--metadata", help="JSON metadata to attach to the message")
@click.option("--payload", help="Raw JSON payload to insert; overrides other fields")
@click.option("--table", help="Supabase table for messages (default from config)")
@click.option("--event", "broadcast_event", default="direct_message", help="Event type used in broadcast payload")
@click.option("--upsert", is_flag=True, help="Use upsert when storing the message")
def direct_message(
    channel: str | None,
    sender: str | None,
    recipient: str | None,
    content: str | None,
    metadata: str | None,
    payload: str | None,
    table: str | None,
    broadcast_event: str,
    upsert: bool,
) -> None:
    """Persist a direct message and broadcast it to teammates."""

    try:
        config = _load_realtime_config(channel)
    except RuntimeError as exc:
        print_error(str(exc))
        return

    try:
        supabase_client = _build_supabase_client(config["project_url"], config["api_key"])
    except RuntimeError as exc:
        print_error(str(exc))
        return

    if payload:
        try:
            message_payload = json.loads(payload)
        except json.JSONDecodeError as err:
            raise click.UsageError(f"Invalid JSON payload: {err}") from err
    else:
        if not content:
            raise click.UsageError("Provide --content or --payload to describe the message")
        message_payload = {"content": content}
        if sender:
            message_payload["sender"] = sender
        if recipient:
            message_payload["recipient"] = recipient
        if metadata:
            try:
                message_payload["metadata"] = json.loads(metadata)
            except json.JSONDecodeError as err:
                raise click.UsageError(f"Invalid metadata JSON: {err}") from err

    channel_config = RealtimeChannelConfig.from_topic(config["topic"])
    channel_config = replace(channel_config, broadcast_ack=True, broadcast_self=True)

    async def _run_direct_message() -> Dict[str, Any]:
        async with SupabaseRealtimeClient(
            project_url=config["project_url"],
            api_key=config["api_key"],
            channel=channel_config,
            realtime_url=config["realtime_url"],
        ) as realtime_client:
            messenger = RealtimeMessenger(
                realtime_client,
                supabase_client,
                note_table=config["note_table"],
                message_table=config["message_table"],
            )
            return await messenger.send_direct_message(
                message_payload,
                table=table,
                broadcast_event=broadcast_event,
                upsert=upsert,
            )

    try:
        stored = asyncio.run(_run_direct_message())
    except Exception as exc:  # pragma: no cover - user feedback
        print_error(f"Direct message failed: {exc}")
        return

    console.print(Pretty({"message": stored}, indent_guides=True))
    print_success("Direct message stored and broadcast.")
