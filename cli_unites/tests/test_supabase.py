import pytest
from cli_unites.database.create_client import supabase


def test_supabase_client():
    """Test Supabase client was created successfully"""
    try:
        print(" ")
        print("======Testing Supabase Client======")
        # Check that the client exists and has the expected attributes
        assert supabase is not None, "Supabase client is None"
        assert hasattr(supabase, 'auth'), "Supabase client missing auth"
        assert hasattr(supabase, 'table'), "Supabase client missing table method"
        print("Supabase client created successfully!")
    except Exception as e:
        print(f"Client test failed: {e}")
        pytest.fail(f"Client test failed: {e}")

def test_supabase_connection():
    """Test Supabase connection"""
    try:
        print(" ")
        print("======Connecting to Supabase======")
        response = (
            supabase.table("connect")
            .select("*")
            .execute()
        )
        print(f"Response: {response}")
        #assert response is not None
    except Exception as e:
        print(f"Connection failed: {e}")
        pytest.fail(f"Connection failed: {e}")
