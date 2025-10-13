alter table users enable row level security;
alter table users_teams enable row level security;
alter table teams enable row level security;
alter table projects enable row level security;
alter table notes enable row level security;


create policy "Users can view own record"
on users
for select
using (id = auth.uid());

create policy "Users can update own record"
on users
for update
using (id = auth.uid());

create policy "Users can see their team memberships"
on users_teams
for select
using (user_id = auth.uid());

create policy "Users can view teams they belong to"
on teams
for select
using (
  exists (
    select 1
    from users_teams ut
    where ut.team_id = teams.id
      and ut.user_id = auth.uid()
  )
);
create policy "Users can view projects of their teams"
on projects
for select
using (
  exists (
    select 1
    from users_teams ut
    where ut.team_id = projects.team_id
      and ut.user_id = auth.uid()
  )
);


create policy "Users can view their own notes or team notes"
on notes
for select
using (
  user_id = auth.uid()
  or exists (
    select 1
    from projects p
    join users_teams ut on ut.team_id = p.team_id
    where p.id = notes.project_id
      and ut.user_id = auth.uid()
  )
);

create policy "Users can update their own notes"
on notes
for update
using (user_id = auth.uid());

create policy "Users can delete their own notes"
on notes
for delete
using (user_id = auth.uid());

alter table paths enable row level security;
alter table notes_tags enable row level security;
alter table tags enable row level security;


