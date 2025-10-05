from dotenv import load_dotenv
from supabase import create_client, Client
from supabase.client import ClientOptions
import psycopg2
import os

load_dotenv()

# supabase connection variables
url: str = os.getenv("SUPABASE_URL")
key: str = os.getenv("SUPABASE_KEY")

# creating supabase client
supabase: Client = create_client(url, key)
