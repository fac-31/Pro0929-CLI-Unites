import pytest
from supabase.create_client import supabase

class TestSupabaseConnection:

    @pytest.fixture
    def supabase_client(self):
        """Setup: Create client before each test"""
        try:
            # Try to get auth session (doesn't require tables)
            response = supabase.auth.get_session()
            print("Connected to Supabase!")
            return response
        except Exception as e:
            print(f"Connection failed: {e}")
