test:
	uv run pytest -s -v

seed:
	uv run python cli_unites/database/seed.py

db_reset:
	bash -c "cd cli_unites/database && supabase start && supabase db reset"

db_push:
	cd cli_unites/database
	supabase db push
	cd ../
