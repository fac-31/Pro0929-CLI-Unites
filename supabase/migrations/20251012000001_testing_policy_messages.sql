-- Temporary testing policy for messages table
-- This allows all operations without authentication for development/testing
-- REMOVE THIS IN PRODUCTION!

-- Drop the restrictive policies
drop policy if exists "Users can read their own messages" on messages;
drop policy if exists "Users can send messages" on messages;

-- Create a permissive policy for testing
create policy "Allow all operations for testing"
  on messages
  for all
  using (true)
  with check (true);

