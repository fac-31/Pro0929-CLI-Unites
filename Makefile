test:
	uv run pytest -s -v

seed:
	uv run python cli_unites/database/seed.py

db_reset:
	cd cli_unites/database/supabase
	supabase db reset
	cd ../../

db_push:
	cd cli_unites/database/supabase
	supabase db push
	cd ../../
