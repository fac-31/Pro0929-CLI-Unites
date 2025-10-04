1. Developer Workflow (How you’ll run & interact with it)

Think of it like git commit, but for notes:

Create a note

notes add "Investigating why login is slow"


Add multiline notes (opens $EDITOR like git commit)

notes add


List notes

notes list


Search notes (locally or via Supabase RAG)

notes search "login performance"


Show note details

notes show <note_id>


Sync notes with Supabase

notes sync


Team setup/auth

notes auth login
notes team switch my-team

2. What a note should contain

Each note could be a JSON record with metadata:

{
  "id": "uuid",
  "text": "Investigating login issue in AuthController",
  "timestamp": "2025-09-29T14:12:33Z",
  "cwd": "/Users/anna/projects/my-app/src/auth",
  "file_context": "AuthController.js",
  "git_commit": "a8d3f5b",
  "team_id": "team_123"
}


How to populate automatically:

File context: infer from $PWD or an optional --file flag

Git commit: run git rev-parse HEAD if inside a repo

Timestamp: auto-generated

Team/user: pulled from config

3. Saving Notes in Supabase

Table schema:

create table notes (
  id uuid primary key default gen_random_uuid(),
  user_id uuid references auth.users,
  team_id uuid references teams,
  text text,
  cwd text,
  file_context text,
  git_commit text,
  created_at timestamp with time zone default now()
);


Add pgvector column embedding vector(1536) for RAG search.

When you notes add, CLI:

Stores note locally (SQLite or JSON file for offline mode).

If online, calls Supabase API → inserts note + embedding.

4. Querying Notes via RAG

CLI command:

notes search "how did we debug login last week?"


Flow:

CLI sends query → Supabase function.

Supabase generates embedding, does vector similarity search.

Returns relevant notes.

Output could be pretty-printed in terminal (like git log --oneline).

5. Authentication & Teams

Auth flow:

notes auth login → opens Supabase OAuth in browser → returns JWT saved in ~/.notes/config.json.

notes team switch <team_id> → saves current team in config.

Config file example:

{
  "user_id": "uuid",
  "team_id": "team_123",
  "access_token": "supabase_jwt",
  "refresh_token": "supabase_refresh"
}


CLI automatically refreshes token and reuses stored team_id.

6. Implementation Plan

CLI Scaffolding

Start with your click-app structure (notes add, notes list).

Local Storage

Use SQLite or JSON in ~/.notes/notes.db.

Add auto-insertion of metadata (time, git commit, cwd).

Supabase Backend

Create notes + teams tables.

Add Supabase functions for search + auth.

Enable pgvector for embeddings.

Sync

notes sync → upload unsynced local notes.

Auth

Implement notes auth login/logout.

Store credentials in config file.

RAG Search

Add notes search using Supabase vector similarity.