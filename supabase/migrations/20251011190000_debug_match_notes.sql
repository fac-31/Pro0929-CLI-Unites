-- Function to match notes based on vector similarity (DEBUG version)
-- This version removes the match_threshold from the WHERE clause
-- to return results regardless of their similarity score.
create or replace function match_notes(
  query_embedding vector(384),
  match_threshold float default 0.5,
  match_count int default 10
)
returns table (
  id uuid,
  title text,
  body text,
  user_id uuid,
  project_id uuid,
  path_id uuid,
  created_at timestamptz,
  updated_at timestamptz,
  similarity float
)
language plpgsql stable
security definer
as $$
begin
  -- Return matching notes
  return query
    select
      notes.id,
      notes.title,
      notes.body,
      notes.user_id,
      notes.project_id,
      notes.path_id,
      notes.created_at,
      notes.updated_at,
      1 - (notes.body_embedding <=> query_embedding) as similarity
    from notes
    where notes.body_embedding is not null
    order by notes.body_embedding <=> query_embedding
    limit match_count;
end;
$$;
