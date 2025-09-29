"""Core utilities for cli-unites."""

from .config import ConfigManager, load_config, save_config, update_config
from .db import Database, get_connection
from .git import get_git_context
from .supabase import SupabaseClient
from .embeddings import embed_text

__all__ = [
    "ConfigManager",
    "load_config",
    "save_config",
    "update_config",
    "Database",
    "get_connection",
    "get_git_context",
    "SupabaseClient",
    "embed_text",
]
