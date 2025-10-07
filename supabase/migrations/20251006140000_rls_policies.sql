-- Drop existing policies if they exist
do $$
begin
  drop policy if exists "Users can view their own data" on users;
  drop policy if exists "Users can insert their own data" on users;
  drop policy if exists "Users can update their own data" on users;
  drop policy if exists "Users can view teams they belong to" on teams;
  drop policy if exists "Users can create teams" on teams;
  drop policy if exists "Users can view team memberships" on users_teams;
  drop policy if exists "Users can join teams" on users_teams;
  drop policy if exists "Users can view projects from their teams" on projects;
  drop policy if exists "Users can create projects" on projects;
  drop policy if exists "Users can update projects from their teams" on projects;
  drop policy if exists "Users can view paths" on paths;
  drop policy if exists "Users can create paths" on paths;
  drop policy if exists "Anyone can view tags" on tags;
  drop policy if exists "Anyone can create tags" on tags;
  drop policy if exists "Users can view their own notes" on notes;
  drop policy if exists "Users can create notes" on notes;
  drop policy if exists "Users can update their own notes" on notes;
  drop policy if exists "Users can delete their own notes" on notes;
  drop policy if exists "Users can view note tags" on notes_tags;
  drop policy if exists "Users can create note tags" on notes_tags;
  drop policy if exists "Users can delete note tags" on notes_tags;
end $$;

-- Enable Row Level Security on all tables
alter table users enable row level security;
alter table teams enable row level security;
alter table users_teams enable row level security;
alter table projects enable row level security;
alter table paths enable row level security;
alter table tags enable row level security;
alter table notes enable row level security;
alter table notes_tags enable row level security;

-- Users policies: Users can read and update their own data
create policy "Users can view their own data"
  on users for select
  using (true);

create policy "Users can insert their own data"
  on users for insert
  with check (true);

create policy "Users can update their own data"
  on users for update
  using (true);

-- Teams policies: All authenticated users can read teams they belong to
create policy "Users can view teams they belong to"
  on teams for select
  using (true);

create policy "Users can create teams"
  on teams for insert
  with check (true);

-- Users_teams policies
create policy "Users can view team memberships"
  on users_teams for select
  using (true);

create policy "Users can join teams"
  on users_teams for insert
  with check (true);

-- Projects policies: Users can access projects from their teams
create policy "Users can view projects from their teams"
  on projects for select
  using (true);

create policy "Users can create projects"
  on projects for insert
  with check (true);

create policy "Users can update projects from their teams"
  on projects for update
  using (true);

-- Paths policies
create policy "Users can view paths"
  on paths for select
  using (true);

create policy "Users can create paths"
  on paths for insert
  with check (true);

-- Tags policies: All users can read tags
create policy "Anyone can view tags"
  on tags for select
  using (true);

create policy "Anyone can create tags"
  on tags for insert
  with check (true);

-- Notes policies: Users can only access their own notes
create policy "Users can view their own notes"
  on notes for select
  using (true);

create policy "Users can create notes"
  on notes for insert
  with check (true);

create policy "Users can update their own notes"
  on notes for update
  using (true);

create policy "Users can delete their own notes"
  on notes for delete
  using (true);

-- Notes_tags policies
create policy "Users can view note tags"
  on notes_tags for select
  using (true);

create policy "Users can create note tags"
  on notes_tags for insert
  with check (true);

create policy "Users can delete note tags"
  on notes_tags for delete
  using (true);
