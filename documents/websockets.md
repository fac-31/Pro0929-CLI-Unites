# Web Socket Implementation

I want to create a websocket that updates users when new notes are made by teammates, and that allow them to message teammates. I also want to add alert functionality later.


The cli_unites Python CLI tool will:
- Open a WebSocket connection to Supabase Realtime (wss://<project>.supabase.co/realtime/v1).
- Authenticate using your Supabase anon or service_role key.
- Join a channel, e.g. realtime:public:messages.
- Listen for INSERT, UPDATE, or DELETE events.
- Handle payloads as they arrive

Dependencies: websockets asyncio

## Implementation Plan
- Define configuration inputs (Supabase project ID, anon/service role key, default channel) and decide how the CLI collects them (env vars, config file, or command flags).
- Ensure runtime dependencies are declared (`websockets`, `asyncio`, and any helper libs) and wire them into the package installer metadata.
- Build a reusable Supabase realtime client module that establishes the WebSocket connection, authenticates, joins channels, and exposes async hooks for note updates and teammate messages.
- Extend the CLI command set to launch the realtime client: parse user intent (listen-only vs. send message), start the asyncio loop, and surface payloads in a user-friendly format.
- Implement message-send support by publishing appropriate event payloads back through Supabase RPC or REST endpoints while reusing the realtime session for responses.
- Add integration-focused tests or mocks that exercise connection setup, event callbacks, and CLI command flows; document manual testing steps for live Supabase verification.
- Document follow-up work for alert functionality (e.g., reusable notification interface) so future updates can plug into the realtime event stream.

## Detailed Execution Plan
- [x] Phase 1: Audit current CLI config handling, add Supabase env var support, and document required settings.
- [x] Phase 2: Update packaging metadata to include websocket dependencies and verify local install via pip install -e .
- [x] Phase 3: Implement a SupabaseRealtimeClient class that wraps connection lifecycle, channel subscription, and event dispatch callbacks.
- [x] Phase 4: Introduce CLI commands/subcommands for realtime listen and send flows, wiring them to the client and ensuring graceful shutdown.
- [ ] Phase 5: Create async messaging helpers to publish note updates or direct messages using Supabase REST/RPC while reusing the websocket session.
- [ ] Phase 6: Build automated tests with mocked websocket interactions plus manual testing scripts for staging Supabase projects.
- [ ] Phase 7: Draft alert-system extension notes covering notification triggers, delivery channels, and required API changes.

## Realtime Configuration Inputs
- `SUPABASE_URL` / `--supabase-url`: base project URL such as `https://xyzcompany.supabase.co`.
- `SUPABASE_KEY` / `--supabase-key`: anon or service-role key for authenticating websocket traffic.
- `SUPABASE_REALTIME_URL` / `--supabase-realtime-url`: optional override when the websocket endpoint diverges from the default `wss://<project>.supabase.co/realtime/v1`.
- `SUPABASE_REALTIME_CHANNEL` / `--supabase-realtime-channel`: default channel to subscribe to (defaults to `realtime:public:notes`).
