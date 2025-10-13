# PR: Feature - End-to-End Semantic Search with Supabase

## Summary

This PR completes an end-to-end semantic search feature through supabase

## Key Changes

### 1. Architectural Shift to Supabase
- **Replaced SQLite:** The local `notes.db` file has been replaced with a Supabase backend.
- **New Database Schema:** A new schema has been introduced with tables for `users`, `teams`, `projects`, `notes`, and `tags`, establishing a relational structure for the application.
- **Database Migrations:** The project now uses Supabase's migration system to manage database schema changes declaratively.

### 2. Automatic Vector Embeddings Pipeline
- **Postgres Extensions:** Enables `vector`, `pgmq`, `pg_net`, and `pg_cron` to create a (mostly) in-database processing pipeline.
- **Automatic Embedding:** When a note is sent to the database a trigger automatically queues a job for the embeddings to be processed.
- **Edge Functions:**
    - An `embed` Edge Function processes queued jobs in the background and generates vector embeddings via the OpenAI API. This means the process won't block the user.
    - A `search-embed` Edge Function provides embeddings for semantic search queries.

### 3. Python-Powered Semantic Search
- **Replaced SQL Function:** The initial `match_notes` SQL function has been replaced with a pure Python implementation (`cli_unites/core/match_notes.py`). This was soley done for debugging purposes.
- **Client-Side Logic:** The `Database` class in `db.py` fetches the query embedding and calls the Python-based `match_notes` function to calculate cosine similarity.

### 4. Enhanced CLI Experience
- **New `semantic-search` Command:** A new command has been added to the CLI to expose the new search functionality.
- **Rich Panel Output:** Search results are now displayed in Rich panels, showing the full note body, title, and metadata for a much better user experience.
- **Similarity Score:** The relevance of each search result is clearly indicated with a similarity score displayed prominently in the panel's title.

### 5. Dev
- **Dependencies:** Added `supabase`, `psycopg2-binary`, `vecs`, `openai`, and `deno` to `pyproject.toml`.
- **Makefile:** An updated `Makefile` includes commands for seeding the database, resetting it, and deploying Edge Functions.
- **Seeding Script:** A new `seed.sh` script makes it easy to populate the database with sample data for testing.
- **Documentation:** Added `learnings.md` to share key insights from the development and debugging process.
