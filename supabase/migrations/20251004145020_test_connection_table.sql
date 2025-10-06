-- Users
create table users (
  id uuid primary key default gen_random_uuid(),
  email text unique not null,
  full_name text,
  created_at timestamptz default now()
);

-- Teams
create table teams (
  id uuid primary key default gen_random_uuid(),
  name text not null,
  created_at timestamptz default now()
);

-- Many-to-many: Users can be on multiple teams
create table users_teams (
  user_id uuid references users(id) on delete cascade,
  team_id uuid references teams(id) on delete cascade,
  joined_at timestamptz default now(),
  primary key (user_id, team_id)
);

-- Projects (links to teams)
create table projects (
  id uuid primary key default gen_random_uuid(),
  team_id uuid references teams(id) on delete cascade,
  name text not null,
  absolute_path text not null,  -- /Users/github/cli_tool
  created_at timestamptz default now(),
  unique(team_id, absolute_path)
);

-- Paths within projects (relative to project root)
create table paths (
  id uuid primary key default gen_random_uuid(),
  project_id uuid references projects(id) on delete cascade,
  relative_path text not null,  -- auth/db/utils, auth/db/client
  created_at timestamptz default now(),
  unique(project_id, relative_path)
);

-- Tags (normalized)
create table tags (
  id uuid primary key default gen_random_uuid(),
  name text unique not null,  -- bug, feature, todo, refactor
  created_at timestamptz default now()
);

-- Notes
create table notes (
  id uuid primary key default gen_random_uuid(),
  user_id uuid references users(id) on delete cascade,
  project_id uuid references projects(id) on delete cascade,

  -- Content
  title text not null,
  body text not null,
  --body_embedding vector(384),  -- For semantic search

  -- Optional context
  path_id uuid references paths(id) on delete set null,

  -- Metadata
  created_at timestamptz default now(),
  updated_at timestamptz default now(),

  -- Full-text search
  body_tsv tsvector generated always as (to_tsvector('english', body)) stored
);

-- Many-to-many: Notes can have multiple tags
create table notes_tags (
  note_id uuid references notes(id) on delete cascade,
  tag_id uuid references tags(id) on delete cascade,
  tagged_at timestamptz default now(),
  primary key (note_id, tag_id)
);

-- Indexes for vector similarity search
--create index on notes
--using ivfflat (body_embedding vector_cosine_ops)
--with (lists = 100);

-- Indexes for full-text search
--create index on notes using gin(body_tsv);

-- Indexes for common queries
-- create index on notes(user_id);
-- create index on notes(project_id);
-- create index on notes(path_id);
-- create index on paths(project_id);
-- create index on paths(relative_path);
-- create index on projects(team_id);
-- create index on notes_tags(note_id);
-- create index on notes_tags(tag_id);

-- Trigger to update updated_at timestamp
create or replace function update_updated_at_column()
returns trigger as $$
begin
  new.updated_at = now();
  return new;
end;
$$ language plpgsql;

create trigger update_notes_updated_at
  before update on notes
  for each row
  execute function update_updated_at_column();
