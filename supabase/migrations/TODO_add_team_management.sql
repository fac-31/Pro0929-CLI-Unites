-- Team management schema upgrade

-- 1. Extend teams with metadata fields used by the CLI
alter table if exists public.teams
  add column if not exists description text,
  add column if not exists slug text unique,
  add column if not exists created_by uuid references public.users(id),
  add column if not exists updated_at timestamptz default now();

-- Ensure updated_at stays current
create or replace function public.set_updated_at()
returns trigger as $$
begin
  new.updated_at = now();
  return new;
end;
$$ language plpgsql;

drop trigger if exists set_teams_updated_at on public.teams;
create trigger set_teams_updated_at
before update on public.teams
for each row
execute procedure public.set_updated_at();

-- 2. Enhance users_teams join table with roles and inviter tracking
alter table if exists public.users_teams
  add column if not exists role text default 'member',
  add column if not exists invited_by uuid references public.users(id);

create index if not exists users_teams_team_role_idx on public.users_teams(team_id, role);
create index if not exists users_teams_user_role_idx on public.users_teams(user_id, role);

-- 3. Invitation support table
create table if not exists public.team_invitations (
  code text primary key,
  team_id uuid references public.teams(id) on delete cascade,
  email text not null,
  role text default 'member',
  invited_by uuid references public.users(id),
  expires_at timestamptz,
  redeemed_at timestamptz,
  metadata jsonb default '{}'::jsonb,
  created_at timestamptz default now()
);

create index if not exists team_invitations_team_idx on public.team_invitations(team_id);
create index if not exists team_invitations_email_idx on public.team_invitations(email);

-- 4. Utility: generate invite codes when server-side logic needs them
create or replace function public.generate_invite_code(length int default 6)
returns text
language plpgsql
as $$
declare
  alphabet constant text := 'ABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789';
  result text := '';
begin
  for i in 1..length loop
    result := result || substr(alphabet, 1 + floor(random()*length(alphabet))::int, 1);
  end loop;
  return result;
end;
$$;
