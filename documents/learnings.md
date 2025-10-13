# Learnings from CLI-Unites Semantic Search Debugging

This document summarizes the key discoveries and fixes made while debugging the semantic search functionality of the `notes` CLI tool.

## 1. Client-Side vs. Server-Side Embeddings

The initial error, `AttributeError: 'SyncClient' object has no attribute 'embeddings'`, revealed a core misunderstanding. The `supabase-py` client library does not have a built-in method to generate embeddings directly.

**Discovery:** Embedding generation is a server-side operation that requires calling an AI model (like OpenAI's). The standard and secure practice with Supabase is to handle this within an Edge Function, which keeps API keys and other secrets from being exposed on the client.

## 2. Differentiating Edge Function Use Cases

The project already had an `embed` Edge Function, but it was designed for a different purpose.

**Discovery:** There are two primary use cases for embedding generation in this application:

1.  **Asynchronous Background Processing:** For embedding notes when they are created or updated. The existing `embed` function, triggered by a database message queue (`pgmq`), is correctly designed for this.
2.  **Synchronous On-Demand Processing:** For generating an embedding for a user's search query in real-time. This requires a direct, callable endpoint.

**Solution:** A new, dedicated Edge Function, `search-embed`, was created. This function has a single purpose: to receive a text query and immediately return its vector embedding.

## 3. Correctly Invoking Edge Functions from Python

Several errors occurred when trying to call the new Edge Function from the Python client.

**Discoveries & Fixes:**

*   **`TypeError: 'SyncFunctionsClient' object is not callable`**: The correct syntax is `self.client.functions.invoke(...)`, not `self.client.functions().invoke(...)`. The `functions` attribute is an object, not a method.
*   **`AttributeError: 'bytes' object has no attribute 'data'`**: The `invoke` method returns a raw `bytes` object. This response needs to be parsed from JSON using `json.loads()` to be used as a Python dictionary.

## 4. The Importance of Database Trigger Configuration

The most critical issue was that semantic search returned incorrect results because new or updated notes were not being properly embedded.

**Discovery:** The database trigger responsible for queuing embedding jobs was incorrectly configured. The original trigger was set to fire `on update of body_embedding`, meaning it would only run if the embedding column itself was changed, not the note's content.

**Solution:** The trigger definition in the core migration file (`..._test_connection_table.sql`) was corrected to fire `after insert or update of title, body`. This ensures that any change to a note's content will correctly queue a job to regenerate its embedding.

## 5. Production Troubleshooting After a DB Reset

When the database is reset, especially in a production environment, several non-code issues can arise.

**Key Troubleshooting Steps:**

1.  **Verify Environment Secrets:** The `OPENAI_API_KEY` must be set in the Supabase project's secrets, as this is not part of the codebase and is not restored by a reset.
2.  **Check for Enabled Extensions:** Ensure necessary Postgres extensions like `pg_cron` are enabled on the production database instance.
3.  **Review Function Logs:** The logs for the `embed` and `search-embed` functions in the Supabase dashboard are invaluable for diagnosing runtime errors.
