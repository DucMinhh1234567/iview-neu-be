"""
Supabase client setup and initialization.
"""
from supabase import create_client, Client
from config import SUPABASE_URL, SUPABASE_KEY

# Initialize Supabase client
supabase: Client = create_client(SUPABASE_URL, SUPABASE_KEY)


def get_supabase_client() -> Client:
    """
    Get Supabase client instance.
    
    Returns:
        Supabase client
    """
    return supabase


def check_supabase_health() -> bool:
    """
    Check if Supabase connection is healthy.
    
    Returns:
        True if connection is healthy, False otherwise
    """
    try:
        # Try a simple query to check connection
        supabase.table("User").select("user_id").limit(1).execute()
        return True
    except Exception as e:
        print(f"Supabase health check failed: {e}")
        return False

