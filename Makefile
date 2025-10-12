# runs all pytest functions
test:
	uv run pytest -s -v

# seeds the production db
seed:
	./seed.sh

# resets local db
reset:
	supabase db reset --linked

# pushes moigartions to production db
push:
	supabase db push

edge:
	supabase functions deploy embed

i:
	pip3 install -e .
