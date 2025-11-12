"""
Supabase client setup and initialization.
"""
from supabase import create_client, Client
from config import SUPABASE_URL, SUPABASE_KEY

# Initialize Supabase client
supabase: Client = create_client(SUPABASE_URL, SUPABASE_KEY)

# Safe diagnostic: mask key and warn if it looks like anon (no verification)
try:
    _masked = f"{SUPABASE_KEY[:4]}...{SUPABASE_KEY[-4:]}" if isinstance(SUPABASE_KEY, str) and len(SUPABASE_KEY) > 8 else "<invalid>"
    # Try to detect role claim in JWT payload (base64url without padding)
    import base64, json
    _parts = SUPABASE_KEY.split(".")
    _payload_raw = _parts[1] if len(_parts) > 1 else ""
    _padding = "=" * (-len(_payload_raw) % 4)
    _decoded = json.loads(base64.urlsafe_b64decode((_payload_raw + _padding).encode("utf-8"))) if _payload_raw else {}
    _role = _decoded.get("role")
    if _role != "service_role":
        print(f"[Config Warning] SUPABASE_KEY does not look like service_role (role={_role}). Current key (masked): { _masked }")
    else:
        print(f"[Config] Supabase service role key detected (masked): { _masked }")
except Exception as _e:
    # Do not fail app start because of diagnostics
    print(f"[Config Notice] Could not inspect SUPABASE_KEY: {_e}")


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

