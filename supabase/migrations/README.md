# Database Migrations

## Setup for New Contributors

After cloning this repo, you need to create a local-only migration file for your service role key:

1. Create the migration file:
   ```bash
   supabase migration new set_service_role_key_local
   ```

2. Add the following content to the file (replace with your actual service role key):
   ```sql
   -- Local-only migration: DO NOT COMMIT THIS FILE

   create or replace function util.service_role_key()
   returns text
   language sql
   immutable
   security definer
   as $$
     select 'YOUR_SERVICE_ROLE_KEY_HERE'::text;
   $$;
   ```

3. Get your service role key from:
   https://supabase.com/dashboard/project/YOUR_PROJECT_ID/settings/api

4. This file is automatically gitignored, so your key will never be committed.

## Why This Approach?

The service role key is needed for the database to authenticate with Edge Functions when generating embeddings via pg_cron. Since this is a public repo, we can't commit the actual key. Each developer needs their own local-only migration file.
