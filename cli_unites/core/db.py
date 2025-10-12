"""Supabase persistence for notes."""
from __future__ import annotations

import os
import json
from contextlib import contextmanager
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, Generator, Iterable, List, Optional
from uuid import uuid4

from dotenv import load_dotenv
from supabase import create_client, Client
from cli_unites.core.match_notes import match_notes

load_dotenv()


class Database:
    """Thin wrapper around Supabase client for notes operations."""

    def __init__(self, supabase_client: Optional[Client] = None) -> None:
        if supabase_client is not None:
            self.client = supabase_client
        else:
            url = os.getenv("SUPABASE_URL")
            key = os.getenv("SUPABASE_KEY")
            if not url or not key:
                raise ValueError("SUPABASE_URL and SUPABASE_KEY must be set in environment")
            self.client = create_client(url, key)

        # Get current user ID (you may need to implement auth first)
        # For now, we'll use a placeholder or get from auth
        self.user_id = os.getenv("USER_ID")  # TODO: Get from actual auth

    def add_note(
        self,
        title: str,
        body: str,
        tags: Optional[Iterable[str]] = None,
        git_commit: Optional[str] = None,
        git_branch: Optional[str] = None,
        project_path: Optional[str] = None,
        team_id: Optional[str] = None,
    ) -> str:
        note_id = str(uuid4())

        # First, ensure project exists if project_path is provided
        project_id = None
        if project_path:
            project_id = self._ensure_project(project_path)

        # Insert the note
        note_data = {
            "id": note_id,
            "title": title,
            "body": body,
            "user_id": self.user_id,
            "project_id": project_id,
        }

        response = self.client.table("notes").insert(note_data).execute()

        # Handle tags if provided
        if tags:
            self._add_tags_to_note(note_id, tags)

        return note_id

    def _ensure_project(self, project_path: str) -> str:
        """Ensure project exists, create if not. Returns project_id."""
        # Check if project exists
        response = self.client.table("projects").select("id").eq("absolute_path", project_path).execute()

        if response.data:
            return response.data[0]["id"]

        # Create new project (you may need to associate with a team)
        # For now, we'll skip team association
        project_id = str(uuid4())
        project_data = {
            "id": project_id,
            "name": project_path.split("/")[-1],  # Use last part of path as name
            "absolute_path": project_path,
        }
        self.client.table("projects").insert(project_data).execute()
        return project_id

    def _add_tags_to_note(self, note_id: str, tags: Iterable[str]) -> None:
        """Add tags to a note."""
        tag_list = sorted({t.strip() for t in tags if t.strip()})

        for tag_name in tag_list:
            # Ensure tag exists
            response = self.client.table("tags").select("id").eq("name", tag_name).execute()

            if response.data:
                tag_id = response.data[0]["id"]
            else:
                # Create new tag
                tag_id = str(uuid4())
                self.client.table("tags").insert({"id": tag_id, "name": tag_name}).execute()

            # Link tag to note
            self.client.table("notes_tags").insert({
                "note_id": note_id,
                "tag_id": tag_id
            }).execute()

    def list_notes(self, limit: Optional[int] = None, tag: Optional[str] = None) -> List[Dict[str, Any]]:
        query = self.client.table("notes").select("*")

        if tag:
            # Join with tags to filter
            query = query.eq("notes_tags.tags.name", tag)

        query = query.order("created_at", desc=True)

        if limit:
            query = query.limit(limit)

        response = query.execute()
        return response.data

    def get_note(self, note_id: str) -> Optional[Dict[str, Any]]:
        response = self.client.table("notes").select("*").eq("id", note_id).execute()
        return response.data[0] if response.data else None

    def search_notes(self, query: str) -> List[Dict[str, Any]]:
        # Full-text search using PostgreSQL's tsvector
        response = (
            self.client.table("notes")
            .select("*")
            .text_search("body_tsv", query)
            .order("created_at", desc=True)
            .execute()
        )

        # Also search in title (case-insensitive)
        title_results = (
            self.client.table("notes")
            .select("*")
            .ilike("title", f"%{query}%")
            .order("created_at", desc=True)
            .execute()
        )

        # Combine and deduplicate results
        seen_ids = set()
        combined = []
        for item in response.data + title_results.data:
            if item["id"] not in seen_ids:
                seen_ids.add(item["id"])
                combined.append(item)

        return combined

    def semantic_search(self, query: str, limit: int = 10, threshold: float = 0.3) -> List[Dict[str, Any]]:
        """Perform semantic search using vector embeddings."""
        import sys
        import supabase

        # Generate embedding for the query by calling the 'search-embed' edge function
        response = self.client.functions.invoke("search-embed", invoke_options={'body': {'query': query}})
        query_embedding = json.loads(response)['embedding']

        return match_notes(self, query_embedding, limit=limit, threshold=threshold)

    def close(self) -> None:
        # Supabase client doesn't need explicit closing
        pass


@contextmanager
def get_connection(supabase_client: Optional[Client] = None) -> Generator[Database, None, None]:
    db = Database(supabase_client)
    try:
        yield db
    finally:
        db.close()
