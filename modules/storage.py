"""
SQLite Storage Manager for LinkedIn AI Ghostwriter drafts and generation history.
"""

import json
import sqlite3
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional

DB_DIR = Path(__file__).resolve().parent.parent / "data"
DB_PATH = DB_DIR / "ghostwriter.db"


def get_db_connection() -> sqlite3.Connection:
    """Ensure data directory exists and return SQLite connection."""
    DB_DIR.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(str(DB_PATH))
    conn.row_factory = sqlite3.Row
    return conn


def init_db() -> None:
    """Initialize database tables if they do not exist."""
    conn = get_db_connection()
    with conn:
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS drafts (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                title TEXT NOT NULL,
                source_type TEXT NOT NULL,
                source_url TEXT,
                source_title TEXT,
                tone TEXT NOT NULL,
                persona TEXT NOT NULL,
                full_content TEXT NOT NULL,
                hooks_json TEXT,
                body TEXT,
                takeaway TEXT,
                question TEXT,
                hashtags TEXT,
                is_favorite INTEGER DEFAULT 0,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
            """
        )
    conn.close()


def save_draft(
    title: str,
    full_content: str,
    source_type: str = "custom",
    source_url: Optional[str] = None,
    source_title: Optional[str] = None,
    tone: str = "Pragmatic Engineer",
    persona: str = "Software & Data Science Professional",
    hooks: Optional[List[str]] = None,
    body: Optional[str] = None,
    takeaway: Optional[str] = None,
    question: Optional[str] = None,
    hashtags: Optional[str] = None,
) -> int:
    """Save a new draft to the database and return its ID."""
    init_db()
    conn = get_db_connection()
    hooks_json = json.dumps(hooks or [])
    now = datetime.now().isoformat()

    with conn:
        cursor = conn.execute(
            """
            INSERT INTO drafts (
                title, source_type, source_url, source_title,
                tone, persona, full_content, hooks_json,
                body, takeaway, question, hashtags, created_at, updated_at
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                title or "Untitled Post",
                source_type,
                source_url or "",
                source_title or "",
                tone,
                persona,
                full_content,
                hooks_json,
                body or "",
                takeaway or "",
                question or "",
                hashtags or "",
                now,
                now,
            ),
        )
        draft_id = cursor.lastrowid
    conn.close()
    return draft_id


def update_draft(draft_id: int, title: str, full_content: str, hashtags: Optional[str] = None) -> bool:
    """Update an existing draft's text content."""
    conn = get_db_connection()
    now = datetime.now().isoformat()
    with conn:
        conn.execute(
            """
            UPDATE drafts
            SET title = ?, full_content = ?, hashtags = COALESCE(?, hashtags), updated_at = ?
            WHERE id = ?
            """,
            (title, full_content, hashtags, now, draft_id),
        )
    conn.close()
    return True


def get_all_drafts(favorites_only: bool = False, search_query: Optional[str] = None) -> List[Dict[str, Any]]:
    """Retrieve all drafts sorted by latest updated."""
    init_db()
    conn = get_db_connection()
    query = "SELECT * FROM drafts WHERE 1=1"
    params: List[Any] = []

    if favorites_only:
        query += " AND is_favorite = 1"

    if search_query:
        query += " AND (title LIKE ? OR full_content LIKE ? OR hashtags LIKE ?)"
        term = f"%{search_query}%"
        params.extend([term, term, term])

    query += " ORDER BY updated_at DESC"

    cursor = conn.execute(query, params)
    rows = cursor.fetchall()
    results = [dict(row) for row in rows]
    conn.close()
    return results


def get_draft_by_id(draft_id: int) -> Optional[Dict[str, Any]]:
    """Retrieve a single draft by ID."""
    init_db()
    conn = get_db_connection()
    cursor = conn.execute("SELECT * FROM drafts WHERE id = ?", (draft_id,))
    row = cursor.fetchone()
    conn.close()
    return dict(row) if row else None


def delete_draft(draft_id: int) -> bool:
    """Delete a draft by ID."""
    conn = get_db_connection()
    with conn:
        conn.execute("DELETE FROM drafts WHERE id = ?", (draft_id,))
    conn.close()
    return True


def toggle_favorite(draft_id: int) -> bool:
    """Toggle favorite status of a draft."""
    conn = get_db_connection()
    with conn:
        conn.execute(
            """
            UPDATE drafts
            SET is_favorite = CASE WHEN is_favorite = 1 THEN 0 ELSE 1 END,
                updated_at = ?
            WHERE id = ?
            """,
            (datetime.now().isoformat(), draft_id),
        )
    conn.close()
    return True


def export_drafts_json() -> str:
    """Export all saved drafts as a formatted JSON string."""
    drafts = get_all_drafts()
    return json.dumps(drafts, indent=2, default=str)


def export_drafts_markdown() -> str:
    """Export all saved drafts as a consolidated Markdown file."""
    drafts = get_all_drafts()
    md_lines = ["# LinkedIn Post Drafts & Archives\n"]
    for d in drafts:
        md_lines.append(f"## {d['title']}")
        md_lines.append(f"- **Created:** {d['created_at']} | **Tone:** {d['tone']} | **Source:** {d['source_type']}")
        if d.get("source_url"):
            md_lines.append(f"- **URL:** {d['source_url']}")
        md_lines.append("\n```text")
        md_lines.append(d["full_content"])
        md_lines.append("```\n---\n")
    return "\n".join(md_lines)
