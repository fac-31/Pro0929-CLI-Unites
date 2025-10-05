# runs all pytest functions
test:
	uv run pytest -s -v

# seeds the production db
seed:
	uv run python cli_unites/database/seed.py

# resets local db
reset:
	supabase db reset

# pushes moigartions to production db
push:
	supabase db push
