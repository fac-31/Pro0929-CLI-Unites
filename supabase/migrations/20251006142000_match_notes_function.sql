-- Function to match notes based on vector similarity
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
language sql stable
as $$
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
    and 1 - (notes.body_embedding <=> query_embedding) > match_threshold
  order by notes.body_embedding <=> query_embedding
  limit match_count;
$$;
