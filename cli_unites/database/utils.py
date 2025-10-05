from create_client.py import supabase

create_table = (
    supabase.table("commits")
    .insert({"id": 1, "name": "test"})
    .execute()
    print("table created")
)

get_table = (
    supabase.table("test")
    .select("*")
    .execute()
    print("table fetched")
)
