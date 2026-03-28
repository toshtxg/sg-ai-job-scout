from supabase import create_client, Client

_client: Client | None = None


def get_client() -> Client:
    """Return a singleton Supabase client."""
    global _client
    if _client is None:
        from app.utils.config import SUPABASE_URL, SUPABASE_KEY

        _client = create_client(SUPABASE_URL, SUPABASE_KEY)
    return _client
