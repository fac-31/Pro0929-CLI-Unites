# This is a placeholder file that we can use to seed the production database
# Run `uv run seed` to run this file
from create_client import supabase
import os

# Insert seed data
supabase.table("connect").insert([
    {"name": "Anna"},
    {"name": "Rich"},
    {"name": "Jaz"},
]).execute()
