"""Supabase database connection."""

from supabase import Client, create_client

from app.core.config import Settings


def create_database(settings: Settings) -> Client:
    """
    Create Supabase client.
    """

    return create_client(
        settings.supabase_url,
        settings.supabase_secret_key.get_secret_value(),
    )
