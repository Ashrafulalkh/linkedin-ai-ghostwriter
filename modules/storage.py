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
    conn = sqlite3.connect(str(DB_PATH), timeout=10.0)
    conn.row_factory = sqlite3.Row
    # Enable WAL mode for better concurrency between UI and background scheduler
    conn.execute("PRAGMA journal_mode=WAL;")
    return conn


def init_db() -> None:
    """Initialize database tables and perform automatic schema migrations if needed."""
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
                status TEXT DEFAULT 'draft',
                scheduled_at TIMESTAMP,
                published_at TIMESTAMP,
                post_urn TEXT,
                post_url TEXT,
                publish_error TEXT,
                access_token TEXT,
                author_urn TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
            """
        )

        # Automatic schema migration for existing SQLite databases
        cursor = conn.execute("PRAGMA table_info(drafts)")
        existing_cols = {row["name"] for row in cursor.fetchall()}

        new_columns = {
            "status": "TEXT DEFAULT 'draft'",
            "scheduled_at": "TIMESTAMP",
            "published_at": "TIMESTAMP",
            "post_urn": "TEXT",
            "post_url": "TEXT",
            "publish_error": "TEXT",
            "access_token": "TEXT",
            "author_urn": "TEXT",
        }

        for col_name, col_def in new_columns.items():
            if col_name not in existing_cols:
                conn.execute(f"ALTER TABLE drafts ADD COLUMN {col_name} {col_def}")

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
    status: str = "draft",
    scheduled_at: Optional[str] = None,
    access_token: Optional[str] = None,
    author_urn: Optional[str] = None,
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
                body, takeaway, question, hashtags,
                status, scheduled_at, access_token, author_urn,
                created_at, updated_at
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
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
                status,
                scheduled_at,
                access_token or "",
                author_urn or "",
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


def schedule_draft(
    draft_id: int,
    scheduled_at_iso: str,
    access_token: Optional[str] = None,
    author_urn: Optional[str] = None,
) -> bool:
    """Schedule a draft for automatic publishing at a specific ISO timestamp."""
    conn = get_db_connection()
    now = datetime.now().isoformat()
    with conn:
        conn.execute(
            """
            UPDATE drafts
            SET status = 'scheduled',
                scheduled_at = ?,
                publish_error = NULL,
                access_token = CASE WHEN ? IS NOT NULL AND ? != '' THEN ? ELSE access_token END,
                author_urn = CASE WHEN ? IS NOT NULL AND ? != '' THEN ? ELSE author_urn END,
                updated_at = ?
            WHERE id = ?
            """,
            (
                scheduled_at_iso,
                access_token, access_token, access_token,
                author_urn, author_urn, author_urn,
                now,
                draft_id,
            ),
        )
    conn.close()
    return True


def cancel_scheduled_draft(draft_id: int) -> bool:
    """Cancel scheduled publishing and revert draft status back to 'draft'."""
    conn = get_db_connection()
    now = datetime.now().isoformat()
    with conn:
        conn.execute(
            """
            UPDATE drafts
            SET status = 'draft',
                scheduled_at = NULL,
                publish_error = NULL,
                updated_at = ?
            WHERE id = ?
            """,
            (now, draft_id),
        )
    conn.close()
    return True


def mark_draft_published(
    draft_id: int,
    post_urn: Optional[str] = None,
    post_url: Optional[str] = None,
) -> bool:
    """Mark a draft as successfully published to LinkedIn."""
    conn = get_db_connection()
    now = datetime.now().isoformat()
    urn_val = str(post_urn) if post_urn is not None else None
    url_val = str(post_url) if post_url is not None else None
    with conn:
        conn.execute(
            """
            UPDATE drafts
            SET status = 'published',
                published_at = ?,
                post_urn = COALESCE(?, post_urn),
                post_url = COALESCE(?, post_url),
                publish_error = NULL,
                updated_at = ?
            WHERE id = ?
            """,
            (now, urn_val, url_val, now, int(draft_id)),
        )
    conn.close()
    return True


def mark_draft_failed(draft_id: int, error_msg: str) -> bool:
    """Mark a draft as failed to auto-publish with the error reason."""
    conn = get_db_connection()
    now = datetime.now().isoformat()
    err_str = str(error_msg or "Unknown error")
    with conn:
        conn.execute(
            """
            UPDATE drafts
            SET status = 'failed',
                publish_error = ?,
                updated_at = ?
            WHERE id = ?
            """,
            (err_str, now, int(draft_id)),
        )
    conn.close()
    return True


def get_due_scheduled_drafts(now_iso: Optional[str] = None) -> List[Dict[str, Any]]:
    """Retrieve all drafts scheduled for publishing on or before current UTC time."""
    init_db()
    conn = get_db_connection()
    cursor = conn.execute(
        """
        SELECT * FROM drafts
        WHERE status = 'scheduled'
          AND scheduled_at IS NOT NULL
        ORDER BY scheduled_at ASC
        """
    )
    rows = cursor.fetchall()
    conn.close()

    try:
        from modules.time_utils import parse_datetime_safe
    except ImportError:
        from .time_utils import parse_datetime_safe

    from datetime import timezone
    now_utc = parse_datetime_safe(now_iso) if now_iso else datetime.now(timezone.utc)
    due_drafts = []

    for row in rows:
        d_dict = dict(row)
        sched_at_str = d_dict.get("scheduled_at")
        if sched_at_str:
            target_utc = parse_datetime_safe(sched_at_str)
            if target_utc <= now_utc:
                due_drafts.append(d_dict)

    return due_drafts


def get_all_drafts(
    favorites_only: bool = False,
    search_query: Optional[str] = None,
    status_filter: Optional[str] = None,
) -> List[Dict[str, Any]]:
    """Retrieve all drafts sorted by latest updated with optional status and search filters."""
    init_db()
    conn = get_db_connection()
    query = "SELECT * FROM drafts WHERE 1=1"
    params: List[Any] = []

    if favorites_only:
        query += " AND is_favorite = 1"

    if status_filter and status_filter.lower() not in ["all", ""]:
        query += " AND status = ?"
        params.append(status_filter.lower())

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
        status_label = d.get("status", "draft").upper()
        md_lines.append(f"## [{status_label}] {d['title']}")
        md_lines.append(f"- **Created:** {d['created_at']} | **Tone:** {d['tone']} | **Source:** {d['source_type']}")
        if d.get("scheduled_at"):
            md_lines.append(f"- **Scheduled At:** {d['scheduled_at']}")
        if d.get("published_at"):
            md_lines.append(f"- **Published At:** {d['published_at']} | **Post URL:** {d.get('post_url', 'N/A')}")
        if d.get("source_url"):
            md_lines.append(f"- **URL:** {d['source_url']}")
        md_lines.append("\n```text")
        md_lines.append(d["full_content"])
        md_lines.append("```\n---\n")
    return "\n".join(md_lines)
