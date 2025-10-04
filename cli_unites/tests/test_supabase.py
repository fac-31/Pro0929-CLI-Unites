import pytest
from cli_unites.database.create_client import supabase


def test_supabase_client():
    """Setup: Create client before each test"""
    try:
        # Try to get auth session (doesn't require tables)
        print(" ")
        print("======Connecting to Supabase======")
        response = supabase.auth.get_session()
        print(f"Response: {response}")
        assert response is not None
    except Exception as e:
        print(f"Connection failed: {e}")
        pytest.fail(f"Connection failed: {e}")

# def test_supabase_connection():
#     """Test Supabase connection"""
#     try:
#         print(" ")
#         print("======Connecting to Supabase======")
#         response = (
#             supabase.table("connect")
#             .select("*")
#             .execute()
#         )
#         print(f"Response: {response}")
#         #assert response is not None
#     except Exception as e:
#         print(f"Connection failed: {e}")
#         pytest.fail(f"Connection failed: {e}")
