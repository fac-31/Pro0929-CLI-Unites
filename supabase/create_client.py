from dotenv import load_dotenv
from supabase import create_client, Client
import psycopg2
import os

load_dotenv()

# supabase connection variables
url: str = os.getenv("SUPABASE_URL")
key: str = os.getenv("SUPABASE_KEY")

# creating supabase client
supabase: Client = create_client(url, key)

# testing connection
try:
    # Try to get auth session (doesn't require tables)
    response = supabase.auth.get_session()
    print("Connected to Supabase!")
except Exception as e:
    print(f"Connection failed: {e}")
