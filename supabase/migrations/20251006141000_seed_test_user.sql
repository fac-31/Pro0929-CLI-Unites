-- Insert a test user for development
insert into users (id, email, full_name)
values (
  '00000000-0000-0000-0000-000000000000',
  'test@example.com',
  'Test User'
)
on conflict (id) do nothing;
