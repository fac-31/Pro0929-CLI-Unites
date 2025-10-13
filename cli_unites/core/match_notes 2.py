import json
from typing import Any, Dict, List

import numpy as np

# OPENAI_API_KEY= os.getenv("OPENAI_API_KEY")


def match_notes(
    self, query_embedding: List[float], limit: int = 10, threshold: float = 0.3
) -> List[Dict[str, Any]]:
    """Perform semantic search using vector embeddings - Pure Python version."""

    print("\n Searching for your notes...")

    # 2. Fetch ALL notes with embeddings from database
    notes = (
        self.client.table("notes")
        .select(
            "id, title, body, user_id, project_id, path_id, created_at, updated_at, body_embedding"
        )
        .not_.is_("body_embedding", "null")
        .execute()
    )

    if not notes.data:
        print("No notes with embeddings found")
        return []

    print(f"Fetched {len(notes.data)} notes")

    # 3. Calculate similarity for each note in Python
    results = []
    for note in notes.data:
        note_embedding = np.array(json.loads(note["body_embedding"]))

        # Calculate cosine similarity
        # similarity = 1 - cosine_distance
        # cosine_distance = 1 - dot(A, B) / (norm(A) * norm(B))

        dot_product = np.dot(query_embedding, note_embedding)
        query_norm = np.linalg.norm(query_embedding)
        note_norm = np.linalg.norm(note_embedding)

        cosine_similarity = dot_product / (query_norm * note_norm)

        # Only include if above threshold
        if cosine_similarity > threshold:
            results.append(
                {
                    "id": note["id"],
                    "title": note["title"],
                    "body": note["body"],
                    "user_id": note["user_id"],
                    "project_id": note["project_id"],
                    "path_id": note["path_id"],
                    "created_at": note["created_at"],
                    "updated_at": note["updated_at"],
                    "similarity": float(cosine_similarity),
                }
            )

    # 4. Sort by similarity (highest first) and limit
    results.sort(key=lambda x: x["similarity"], reverse=True)
    results = results[:limit]

    return results
