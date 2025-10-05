-- The repository -> absolute path
create table repositories (
  id uuid primary key,
  name text not null,
  absolute_path text unique not null,
  created_at timestamptz default now()
);

-- Paths WITHIN the repository -> relative to repo root
create table paths (
  id uuid primary key,
  repository_id uuid references repositories(id),
  relative_path text not null,  -- src/database, src/components/Button.tsx
  parent_path_id uuid references paths(id),  -- NULL for root-level paths
  unique(repository_id, relative_path)
);

-- Branches of the repository
create table branches (
  id uuid primary key,
  repository_id uuid references repositories(id),
  name text not null,  -- main, feature-auth
  unique(repository_id, name)
);

-- Commits
create table commits (
  id uuid primary key,
  repository_id uuid references repositories(id),
  commit_hash text not null,
  commit_message text not null,
  commit_message_embedding vector(384),
  branch_id uuid references branches(id),  -- Which branch was active
  author text,
  created_at timestamptz not null,
  unique(repository_id, commit_hash)
);

-- Notes
create table notes (
  id uuid primary key,
  content text not null,
  content_embedding vector(384),

  -- Location context
  path_id uuid references paths(id),

  -- Git context
  commit_id uuid references commits(id) not null,
  branch_id uuid references branches(id) not null,
  repository_id uuid references repositories(id) not null,

  -- Versioning
  version int not null default 1,
  previous_version_id uuid references notes(id),

  -- Metadata
  created_at timestamptz not null default now(),
  tags text[],
  is_archived boolean default false,

  -- Full-text search
  content_tsv tsvector generated always as (to_tsvector('english', content)) stored
);

-- Indexes for vector similarity search
create index on commits
using ivfflat (commit_message_embedding vector_cosine_ops)
with (lists = 100);

create index on notes
using ivfflat (content_embedding vector_cosine_ops)
with (lists = 100);

-- Indexes for full-text search
create index on notes using gin(content_tsv);

-- Indexes for common queries
create index on notes(commit_id);
create index on notes(branch_id);
create index on notes(path_id);
create index on notes(repository_id);
create index on commits(branch_id);
create index on commits(repository_id);
create index on paths(repository_id);
create index on paths(parent_path_id);
