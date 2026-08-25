"""
Background Scheduler Service for LinkedIn AI Ghostwriter.
Monitors SQLite database for scheduled posts and auto-publishes them to LinkedIn when due.
"""

from __future__ import annotations

import logging
import os
import threading
import time
from datetime import datetime
from typing import Any, Dict, List, Optional

try:
    from modules.linkedin_api import publish_post_to_linkedin
    from modules.storage import (
        get_due_scheduled_drafts,
        mark_draft_failed,
        mark_draft_published,
    )
except ImportError:
    from .linkedin_api import publish_post_to_linkedin
    from .storage import (
        get_due_scheduled_drafts,
        mark_draft_failed,
        mark_draft_published,
    )

logger = logging.getLogger("ghostwriter.scheduler")
if not logger.handlers:
    logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(name)s: %(message)s")

_SCHEDULER_THREAD: Optional[threading.Thread] = None
_SCHEDULER_STOP_EVENT = threading.Event()
_SCHEDULER_LOCK = threading.Lock()
_LAST_RUN_TIMESTAMP: Optional[str] = None
_PROCESSED_COUNT: int = 0


def process_due_scheduled_posts() -> List[Dict[str, Any]]:
    """
    Check database for any scheduled posts that have reached their target publication time,
    and publish them directly to LinkedIn.
    """
    global _LAST_RUN_TIMESTAMP, _PROCESSED_COUNT
    _LAST_RUN_TIMESTAMP = datetime.now().isoformat()
    processed_results: List[Dict[str, Any]] = []

    try:
        due_drafts = get_due_scheduled_drafts()
    except Exception as e:
        logger.error("Failed to query due scheduled drafts: %s", e)
        return []

    if not due_drafts:
        return []

    logger.info("Found %d scheduled draft(s) due for publishing.", len(due_drafts))

    for draft in due_drafts:
        draft_id = draft["id"]
        draft_title = draft.get("title", f"Draft #{draft_id}")
        logger.info("Processing scheduled post #%d: '%s'", draft_id, draft_title)

        # 1. Resolve LinkedIn access token
        access_token = (
            (draft.get("access_token") or "").strip()
            or (os.getenv("LINKEDIN_ACCESS_TOKEN") or "").strip()
        )

        if not access_token:
            err_msg = "Publish failed: No LinkedIn Access Token found for this scheduled post. Please reconnect LinkedIn."
            logger.warning("Draft #%d: %s", draft_id, err_msg)
            mark_draft_failed(draft_id, err_msg)
            processed_results.append({
                "draft_id": draft_id,
                "title": draft_title,
                "success": False,
                "error": err_msg,
            })
            continue

        # 2. Resolve author URN if saved
        author_urn = (draft.get("author_urn") or "").strip() or (os.getenv("LINKEDIN_AUTHOR_URN") or "").strip() or None

        # 3. Publish to LinkedIn
        try:
            pub_res = publish_post_to_linkedin(
                access_token=access_token,
                text_content=draft["full_content"],
                author_urn=author_urn,
                article_url=draft.get("source_url"),
            )

            if pub_res.get("success"):
                post_urn = pub_res.get("post_urn", "")
                post_url = pub_res.get("post_url", "")
                mark_draft_published(draft_id, post_urn=post_urn, post_url=post_url)
                _PROCESSED_COUNT += 1
                logger.info("Successfully published scheduled post #%d to LinkedIn! URL: %s", draft_id, post_url)
                processed_results.append({
                    "draft_id": draft_id,
                    "title": draft_title,
                    "success": True,
                    "post_url": post_url,
                    "post_urn": post_urn,
                })
            else:
                err_msg = pub_res.get("error", "LinkedIn API returned an unspecified error.")
                mark_draft_failed(draft_id, err_msg)
                logger.error("Failed to publish scheduled post #%d: %s", draft_id, err_msg)
                processed_results.append({
                    "draft_id": draft_id,
                    "title": draft_title,
                    "success": False,
                    "error": err_msg,
                })
        except Exception as e:
            err_msg = f"Unexpected exception during auto-publish: {str(e)}"
            mark_draft_failed(draft_id, err_msg)
            logger.exception("Exception publishing draft #%d: %s", draft_id, e)
            processed_results.append({
                "draft_id": draft_id,
                "title": draft_title,
                "success": False,
                "error": err_msg,
            })

    return processed_results


def _scheduler_loop(interval_seconds: int = 15) -> None:
    """Background polling worker function."""
    logger.info("Background scheduler daemon loop started (polling every %ds).", interval_seconds)
    while not _SCHEDULER_STOP_EVENT.is_set():
        try:
            process_due_scheduled_posts()
        except Exception as e:
            logger.error("Error in scheduler cycle: %s", e)

        # Sleep in small increments for responsive shutdown
        for _ in range(interval_seconds * 2):
            if _SCHEDULER_STOP_EVENT.is_set():
                break
            time.sleep(0.5)

    logger.info("Background scheduler daemon loop stopped.")


def start_background_scheduler(interval_seconds: int = 15) -> bool:
    """
    Start the background thread daemon if not already running.
    Safe to call multiple times across Streamlit script reruns.
    """
    global _SCHEDULER_THREAD
    with _SCHEDULER_LOCK:
        if _SCHEDULER_THREAD is not None and _SCHEDULER_THREAD.is_alive():
            return True

        _SCHEDULER_STOP_EVENT.clear()
        _SCHEDULER_THREAD = threading.Thread(
            target=_scheduler_loop,
            args=(interval_seconds,),
            name="LinkedInGhostwriter-SchedulerDaemon",
            daemon=True,
        )
        _SCHEDULER_THREAD.start()
        logger.info("Background scheduler thread started successfully.")
        return True


def stop_background_scheduler() -> None:
    """Stop the background scheduler thread daemon."""
    global _SCHEDULER_THREAD
    with _SCHEDULER_LOCK:
        _SCHEDULER_STOP_EVENT.set()
        if _SCHEDULER_THREAD is not None and _SCHEDULER_THREAD.is_alive():
            _SCHEDULER_THREAD.join(timeout=2.0)
        _SCHEDULER_THREAD = None


def get_scheduler_info() -> Dict[str, Any]:
    """Return runtime metadata and health status of the background scheduler."""
    is_running = _SCHEDULER_THREAD is not None and _SCHEDULER_THREAD.is_alive()
    return {
        "is_running": is_running,
        "last_run_timestamp": _LAST_RUN_TIMESTAMP,
        "processed_count": _PROCESSED_COUNT,
        "thread_name": _SCHEDULER_THREAD.name if is_running and _SCHEDULER_THREAD else None,
    }
