-- Ensure notes are directly associated with teams for quicker filtering

alter table if exists public.notes
  add column if not exists team_id uuid references public.teams(id);

-- Backfill new column using existing project -> team relationship when available.
update public.notes n
set team_id = p.team_id
from public.projects p
where n.project_id = p.id
  and n.team_id is distinct from p.team_id;

-- Helpful index for team-scoped queries.
create index if not exists notes_team_id_idx on public.notes(team_id);
