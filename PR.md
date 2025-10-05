# Supabase Branch Changes

## Commits
- debcdb8: feat: supabase unfinished setup
- b33efdd: chore: changed python version to 3.9
- 5924488: feat: still unfinished supabase connection
- f78e647: refactor: moved all folders into cli_unites to fix compiling error
- f78e647: feat: adds supabase migrations
- 24fb602: misc: lots of small changes made. Tests pass now for supabase connection
- 7fd1eba: refactor: moved supabase into database folder, and added a makefile to run dev commands
- 84f5cde: config: filters out supabase drecation warnings

## Changes Summary

### Python Version Update
- Updated minimum Python version from 3.8 to 3.9 in pyproject.toml

### Project Structure Refactor
- Moved all test files from `tests/` to `cli_unites/tests/` to fix compilation issues
- Moved workflow files from `workflows/` to `cli_unites/workflows/`
- Organized Supabase files into `cli_unites/database/` directory structure

### Supabase Integration
Added new dependencies:
- psycopg2-binary>=2.9.10
- python-dotenv>=1.1.1
- supabase>=2.20.0

Created database infrastructure:
- `cli_unites/database/create_client.py` - Supabase client initialization using environment variables
- `cli_unites/database/seed.py` - Database seeding script
- `cli_unites/database/utils.py` - Database utility functions (placeholder)
- `cli_unites/database/supabase/` - Supabase configuration and temp files

### Database Migration
- Created migration: `20251004145020_test_connection_table.sql`
  - Creates `connect` table with id and name fields
- Added seed.sql with test data

### Configuration Files
- Added `.env` file with database credentials (DATABASE_URL, SUPABASE_KEY, SUPABASE_URL)
- Added `Makefile` with commands:
  - `test` - Run pytest with verbose output
  - `seed` - Run database seeding script
  - `db_reset` - Reset Supabase database
  - `db_push` - Push changes to Supabase database

### Testing
- Added `cli_unites/tests/test_supabase.py` with:
  - Test for Supabase client creation
  - Test for Supabase database connection
- Added pytest configuration to filter out Supabase deprecation warnings in pyproject.toml

### Environment Files
Added Supabase temp/config files in `cli_unites/database/supabase/.temp/`:
- Project reference, CLI version, Postgres version, GoTrue version, REST version, pooler URL
- Current branch tracking
