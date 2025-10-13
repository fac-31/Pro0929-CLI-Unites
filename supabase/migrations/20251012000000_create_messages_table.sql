-- Messages table for direct messaging between team members
create table messages (
  id uuid primary key default gen_random_uuid(),
  sender text not null,
  recipient text not null,
  content text not null,
  metadata jsonb,
  created_at timestamptz default now()
);

-- Indexes for efficient querying
create index on messages(sender);
create index on messages(recipient);
create index on messages(created_at desc);

-- Enable realtime for messages table
alter publication supabase_realtime add table messages;

-- Row Level Security (RLS) policies
alter table messages enable row level security;

-- Policy: Users can read messages where they are sender or recipient
create policy "Users can read their own messages"
  on messages for select
  using (
    auth.jwt() ->> 'sub' = sender 
    or auth.jwt() ->> 'sub' = recipient
  );

-- Policy: Users can insert messages where they are the sender
create policy "Users can send messages"
  on messages for insert
  with check (auth.jwt() ->> 'sub' = sender);

-- For development/testing: Allow all operations (REMOVE IN PRODUCTION)
-- Uncomment these lines if you want to test without authentication:
-- drop policy if exists "Users can read their own messages" on messages;
-- drop policy if exists "Users can send messages" on messages;
-- create policy "Allow all for testing" on messages for all using (true);

