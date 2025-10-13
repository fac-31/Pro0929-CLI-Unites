-- Enable realtime for notes table
-- This allows the CLI to subscribe to INSERT, UPDATE, DELETE events on notes

alter publication supabase_realtime add table notes;

-- Also ensure other tables have realtime enabled if needed
alter publication supabase_realtime add table projects;
alter publication supabase_realtime add table tags;
alter publication supabase_realtime add table notes_tags;

