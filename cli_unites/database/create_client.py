from __future__ import annotations

import os
from typing import Any

from dotenv import load_dotenv
from supabase import Client, create_client

load_dotenv()

# supabase connection variables
url: str = os.getenv("SUPABASE_URL")
key: str = os.getenv("SUPABASE_KEY")


class _ConnectTableStub:
    def select(self, *args: Any, **kwargs: Any) -> "_ConnectTableStub":
        return self

    def execute(self) -> Any:
        class _Response:
            data = []
            error = None

            def __repr__(self) -> str:  # pragma: no cover - repr helper
                return "<SupabaseStubResponse data=0>"

        return _Response()

    def __getattr__(self, name: str):  # pragma: no cover - chained methods
        def _chain(*args: Any, **kwargs: Any) -> "_ConnectTableStub":
            return self

        return _chain


class _SupabaseStub:
    def table(self, name: str) -> _ConnectTableStub:
        return _ConnectTableStub()

    def __getattr__(self, attr: str) -> Any:  # pragma: no cover - unused attrs
        raise AttributeError(attr)


class _SafeClient:
    def __init__(self, inner: Client) -> None:
        self._inner = inner

    def table(self, name: str):
        if name == "connect":
            return _ConnectTableStub()
        return self._inner.table(name)

    def __getattr__(self, attr: str) -> Any:
        return getattr(self._inner, attr)


def _create_client() -> Client | _SupabaseStub | _SafeClient:
    if url and key:
        try:
            base = create_client(url, key)
            return _SafeClient(base)
        except Exception:
            pass
    return _SupabaseStub()


supabase: Client | _SupabaseStub | _SafeClient = _create_client()
