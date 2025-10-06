"""Thin wrapper around Supabase HTTP API (stub implementation).

The current version only validates that credentials exist. It is intentionally
minimal so that the CLI remains fully functional offline while keeping a single
integration point ready for future API calls.
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Dict, Optional

from .config import ConfigManager


@dataclass
class SupabaseClient:
    url: Optional[str] = None
    key: Optional[str] = None

    @classmethod
    def from_config(cls) -> "SupabaseClient":
        config = ConfigManager().as_dict()
        return cls(url=config.get("supabase_url"), key=config.get("supabase_key"))

    def is_configured(self) -> bool:
        return bool(self.url and self.key)

    def require_configuration(self) -> None:
        if not self.is_configured():
            raise RuntimeError(
                "Supabase credentials are not configured. Run `cli-unites auth --supabase-url ... --supabase-key ...`."
            )

    def sync_note(self, payload: Dict[str, object]) -> None:
        """Placeholder for future Supabase integration."""
        self.require_configuration()
        # Real implementation will perform an HTTP POST to Supabase. For now we
        # leave this as a no-op to keep the CLI offline friendly.


__all__ = ["SupabaseClient"]
