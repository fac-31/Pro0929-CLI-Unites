# 🔌 Add Realtime WebSocket Support for Team Collaboration

## Overview
This PR implements WebSocket-based realtime functionality for the CLI-Unites tool, enabling team members to receive live updates when notes are created/updated and to send direct messages to teammates through the CLI.

## ✨ Features Added

### 1. **Realtime Module** (`cli_unites/realtime/`)
- **`SupabaseRealtimeClient`**: Async WebSocket client for Supabase Realtime
  - Handles connection lifecycle, channel subscriptions, and event dispatch
  - Automatic heartbeat management (25s interval)
  - Graceful shutdown with proper cleanup
  - Support for both async iteration and callback-based message handling
  
- **`RealtimeMessenger`**: High-level coordinator for persistence + broadcasting
  - `publish_note_update()`: Upserts notes and broadcasts changes
  - `send_direct_message()`: Stores and broadcasts direct messages
  - Generic `store_payload()` and `invoke_rpc()` helpers

### 2. **CLI Commands** (`notes realtime`)
Four new subcommands for realtime operations:

- **`notes realtime listen`**: Stream live database changes to terminal
  - Filter by event types (INSERT, UPDATE, DELETE)
  - Pretty-printed or raw JSON output
  - Configurable channel subscription

- **`notes realtime send`**: Broadcast messages to teammates
  - Support for plain text or structured JSON payloads
  - Acknowledgment and self-broadcast options

- **`notes realtime note-update`**: Persist and broadcast note changes
  - Update notes via CLI options or JSON payload
  - Automatic broadcast to subscribed team members

- **`notes realtime direct-message`**: Send direct messages
  - Structured messaging with sender/recipient/content
  - Optional metadata attachment
  - Message persistence with broadcast

### 3. **Database Migrations**

**`20251012000000_create_messages_table.sql`**:
- New `messages` table for direct team messaging
- Schema: sender, recipient, content, metadata (JSONB), timestamps
- RLS policies for secure message access
- Indexed for efficient querying
- Realtime publication enabled

**`20251012000001_testing_policy_messages.sql`**:
- Temporary permissive policies for development/testing
- ⚠️ **TO BE REMOVED BEFORE PRODUCTION**

**`20251012000002_enable_realtime_notes.sql`**:
- Enables realtime publication for `notes`, `projects`, `tags`, and `notes_tags` tables
- Allows live updates when any of these tables change

## 🔧 Technical Implementation

**Architecture Decisions**:
- Built on `websockets` library for clean async/await API
- Connection pooling via context manager (`async with`)
- Phoenix protocol compatibility (Supabase Realtime uses Elixir Phoenix)
- Broadcast vs. Postgres Changes support
- Configuration-driven channel topics

**Configuration Options** (via `notes auth` or environment variables):
- `SUPABASE_REALTIME_URL`: WebSocket endpoint override
- `SUPABASE_REALTIME_CHANNEL`: Default channel (defaults to `realtime:public:notes`)
- `SUPABASE_NOTE_TABLE`: Note persistence table
- `SUPABASE_MESSAGE_TABLE`: Message persistence table

## 📦 Dependencies
- Added `websockets>=12.0` to `pyproject.toml`

## 📚 Documentation
- Comprehensive implementation plan in `documents/websockets.md`
- Execution phases 1-5 completed ✅
- Remaining work: automated tests (phase 6) and alert system design (phase 7)

## 🎯 Use Cases Enabled

1. **Live Team Collaboration**: See when teammates add/update notes in real-time
2. **Direct Messaging**: Send quick messages to team members through the CLI
3. **Event Streaming**: Monitor database changes for integration/debugging
4. **Future Alert System**: Foundation for notification/alert functionality

## 🧪 Testing Status
- ⚠️ Manual testing completed
- ❌ Automated tests pending (see phase 6 in `documents/websockets.md`)
- Testing policies in place but should be replaced with proper RLS before production

## 🔐 Security Considerations
- RLS policies implemented for messages table
- Requires proper authentication via Supabase API key
- Current testing policies are **PERMISSIVE** and must be tightened for production
- WebSocket connection authenticated via API key in query params

## 🚀 Migration Path
1. Run the new migrations (numbered `20251012*`) in order
2. Update configuration with optional realtime settings
3. Install updated dependencies: `uv pip install -e .`
4. Test with: `notes realtime listen`

## 📝 Example Usage

```bash
# Listen for all realtime events on notes
notes realtime listen

# Filter to only INSERT events
notes realtime listen --event INSERT

# Broadcast a message
notes realtime send --message "Deployment complete! 🚀"

# Update a note and broadcast
notes realtime note-update --note-id abc123 --title "Updated Title" --body "New content"

# Send a direct message
notes realtime direct-message --sender user1 --recipient user2 --content "Great work!"
```

## 🔮 Future Work
- Phase 6: Automated WebSocket testing with mocks
- Phase 7: Alert system design (notifications, triggers, delivery channels)
- Production RLS policy refinement
- Rate limiting for broadcasts
- Presence tracking (who's online)

---

**Related Documentation**: `documents/websockets.md`  
**Breaking Changes**: None (purely additive)  
**Database Changes**: Yes (3 new migrations)

