"""
Automated Unit and Integration Tests for LinkedIn AI Ghostwriter.
"""

import json
import unittest
from datetime import datetime, timedelta
from unittest.mock import MagicMock, patch
from modules.storage import (
    init_db,
    save_draft,
    get_all_drafts,
    get_draft_by_id,
    update_draft,
    delete_draft,
    toggle_favorite,
    schedule_draft,
    cancel_scheduled_draft,
    mark_draft_published,
    mark_draft_failed,
    get_due_scheduled_drafts,
    export_drafts_json,
    export_drafts_markdown,
)
from modules.rss_service import clean_html_summary, FEEDS_CATALOG, fetch_single_feed
from modules.scraper_service import scrape_article_content
from modules.ai_generator import LinkedInPostStructure, build_system_prompt, TONE_PROFILES
from modules.scheduler import (
    process_due_scheduled_posts,
    get_scheduler_info,
    start_background_scheduler,
    stop_background_scheduler,
)


class TestStorage(unittest.TestCase):
    """Test SQLite database storage layer."""

    def setUp(self):
        init_db()

    def test_save_and_retrieve_draft(self):
        draft_id = save_draft(
            title="Testing Distributed Systems",
            full_content="Here is a high-signal post about raft consensus.",
            source_type="ArXiv",
            source_url="https://arxiv.org/abs/test",
            tone="Pragmatic Engineer",
            persona="Principal Engineer",
            hooks=["Hook 1", "Hook 2"],
            body="Post body...",
            takeaway="Always evaluate network partition tolerance.",
            question="How do you handle consensus in production?",
            hashtags="#DistributedSystems #Python",
        )
        self.assertIsInstance(draft_id, int)
        
        draft = get_draft_by_id(draft_id)
        self.assertIsNotNone(draft)
        self.assertEqual(draft["title"], "Testing Distributed Systems")
        self.assertEqual(draft["tone"], "Pragmatic Engineer")
        self.assertEqual(draft["status"], "draft")

        # Test toggle favorite
        toggle_favorite(draft_id)
        draft_updated = get_draft_by_id(draft_id)
        self.assertEqual(draft_updated["is_favorite"], 1)

        # Test update draft
        update_draft(draft_id, title="Updated Title", full_content="Updated content")
        draft_edited = get_draft_by_id(draft_id)
        self.assertEqual(draft_edited["title"], "Updated Title")

        # Test export
        json_export = export_drafts_json()
        self.assertIn("Updated Title", json_export)

        md_export = export_drafts_markdown()
        self.assertIn("Updated Title", md_export)

        # Clean up
        delete_draft(draft_id)
        self.assertIsNone(get_draft_by_id(draft_id))

    def test_schedule_and_due_drafts_lifecycle(self):
        """Test scheduling, cancelling, publishing, and due queries."""
        past_time = (datetime.now() - timedelta(minutes=5)).isoformat()
        future_time = (datetime.now() + timedelta(days=2)).isoformat()

        # 1. Save scheduled draft with past timestamp
        draft_id = save_draft(
            title="Scheduled Past Post",
            full_content="Content ready for auto-publish",
            status="scheduled",
            scheduled_at=past_time,
            access_token="test_token_123",
        )
        draft = get_draft_by_id(draft_id)
        self.assertEqual(draft["status"], "scheduled")
        self.assertEqual(draft["scheduled_at"], past_time)

        # 2. Verify due drafts picks it up
        due = get_due_scheduled_drafts()
        due_ids = [d["id"] for d in due]
        self.assertIn(draft_id, due_ids)

        # 3. Mark published
        mark_draft_published(
            draft_id,
            post_urn="urn:li:share:12345",
            post_url="https://www.linkedin.com/feed/update/urn:li:share:12345",
        )
        published_draft = get_draft_by_id(draft_id)
        self.assertEqual(published_draft["status"], "published")
        self.assertIsNotNone(published_draft["published_at"])
        self.assertEqual(published_draft["post_urn"], "urn:li:share:12345")

        # 4. Schedule for future
        schedule_draft(draft_id, scheduled_at_iso=future_time)
        rescheduled_draft = get_draft_by_id(draft_id)
        self.assertEqual(rescheduled_draft["status"], "scheduled")

        # Should not be in due drafts now
        due_now = get_due_scheduled_drafts()
        due_now_ids = [d["id"] for d in due_now]
        self.assertNotIn(draft_id, due_now_ids)

        # 5. Cancel schedule
        cancel_scheduled_draft(draft_id)
        cancelled_draft = get_draft_by_id(draft_id)
        self.assertEqual(cancelled_draft["status"], "draft")
        self.assertIsNone(cancelled_draft["scheduled_at"])

        # 6. Mark failed
        mark_draft_failed(draft_id, error_msg="Simulated API rate limit error")
        failed_draft = get_draft_by_id(draft_id)
        self.assertEqual(failed_draft["status"], "failed")
        self.assertEqual(failed_draft["publish_error"], "Simulated API rate limit error")

        # 7. Status filtering test
        filtered_failed = get_all_drafts(status_filter="failed")
        self.assertTrue(any(d["id"] == draft_id for d in filtered_failed))

        # Clean up
        delete_draft(draft_id)


class TestSchedulerService(unittest.TestCase):
    """Test background scheduler processing engine."""

    def setUp(self):
        init_db()

    @patch("modules.scheduler.publish_post_to_linkedin")
    def test_process_due_scheduled_posts_success(self, mock_publish):
        """Test scheduler successfully publishes due post."""
        mock_publish.return_value = {
            "success": True,
            "post_urn": "urn:li:share:99999",
            "post_url": "https://www.linkedin.com/feed/update/urn:li:share:99999",
            "error": None,
        }

        past_ts = (datetime.now() - timedelta(minutes=10)).isoformat()
        draft_id = save_draft(
            title="Auto Publish Test Post",
            full_content="This is scheduled for auto publishing test.",
            status="scheduled",
            scheduled_at=past_ts,
            access_token="valid_test_token",
        )

        results = process_due_scheduled_posts()
        self.assertTrue(any(r["draft_id"] == draft_id and r["success"] for r in results))

        # Verify DB state
        draft = get_draft_by_id(draft_id)
        self.assertEqual(draft["status"], "published")
        self.assertEqual(draft["post_urn"], "urn:li:share:99999")
        self.assertIsNotNone(draft["published_at"])

        # Clean up
        delete_draft(draft_id)

    @patch("modules.scheduler.publish_post_to_linkedin")
    def test_process_due_scheduled_posts_missing_token(self, mock_publish):
        """Test scheduler handles missing token gracefully."""
        past_ts = (datetime.now() - timedelta(minutes=10)).isoformat()
        draft_id = save_draft(
            title="Auto Publish No Token",
            full_content="Missing token test.",
            status="scheduled",
            scheduled_at=past_ts,
            access_token="",
        )

        with patch.dict("os.environ", {"LINKEDIN_ACCESS_TOKEN": ""}, clear=True):
            results = process_due_scheduled_posts()
            self.assertTrue(any(r["draft_id"] == draft_id and not r["success"] for r in results))

            draft = get_draft_by_id(draft_id)
            self.assertEqual(draft["status"], "failed")
            self.assertIn("No LinkedIn Access Token found", draft["publish_error"])

        # Clean up
        delete_draft(draft_id)

    def test_scheduler_lifecycle(self):
        """Test starting and stopping scheduler daemon."""
        started = start_background_scheduler(interval_seconds=60)
        self.assertTrue(started)
        info = get_scheduler_info()
        self.assertTrue(info["is_running"])
        stop_background_scheduler()
        info_stopped = get_scheduler_info()
        self.assertFalse(info_stopped["is_running"])


class TestRSSService(unittest.TestCase):
    """Test RSS Feed parsing utilities."""

    def test_clean_html_summary(self):
        raw_html = "<p>This is a <b>test</b> with &amp; entities.</p>"
        cleaned = clean_html_summary(raw_html)
        self.assertEqual(cleaned, "This is a test with & entities.")

    def test_feeds_catalog_structure(self):
        self.assertIn("⚡ All Categories", FEEDS_CATALOG)
        self.assertIn("💻 Software Engineering & Architecture", FEEDS_CATALOG)
        self.assertIn("🐍 Python & Data Engineering", FEEDS_CATALOG)
        self.assertIn("🤖 AI, Machine Learning & LLMs", FEEDS_CATALOG)
        for cat, data in FEEDS_CATALOG.items():
            self.assertIn("urls", data)
            self.assertIn("description", data)
            self.assertGreater(len(data["urls"]), 0)


class TestScraperService(unittest.TestCase):
    """Test web scraping extraction."""

    def test_invalid_url(self):
        result = scrape_article_content("invalid-url-no-scheme")
        self.assertFalse(result["success"])
        self.assertIn("Invalid URL", result["error"])


class TestAIGeneratorStructure(unittest.TestCase):
    """Test AI prompt building and Pydantic models."""

    def test_system_prompt_builder(self):
        prompt = build_system_prompt("Data Scientist", "Pragmatic Engineer")
        self.assertIn("Data Scientist", prompt)
        self.assertIn("Pragmatic Engineer", prompt)
        self.assertIn("THE HOOK", prompt)

    def test_pydantic_schema_validation(self):
        sample_data = {
            "hook_option_1": "Most teams build RAG pipelines wrong.",
            "hook_option_2": "Here's why our retrieval latency dropped 80%.",
            "selected_hook": "Most teams build RAG pipelines wrong.",
            "body": "Here are 3 architectural changes we made in production...",
            "technical_takeaway": "Always benchmark embedding chunk sizes.",
            "discussion_question": "What's your biggest challenge with vector databases?",
            "hashtags": ["#MachineLearning", "#Python", "#AI", "#DataEngineering"],
            "full_assembled_post": "Most teams build RAG pipelines wrong.\n\nHere are 3 architectural changes...",
        }
        validated = LinkedInPostStructure(**sample_data)
        self.assertEqual(len(validated.hashtags), 4)
        self.assertEqual(validated.selected_hook, "Most teams build RAG pipelines wrong.")

    def test_openai_missing_key_error(self):
        from modules.ai_generator import generate_linkedin_post
        with patch.dict("os.environ", {"OPENAI_API_KEY": ""}, clear=True):
            res = generate_linkedin_post(
                topic_title="Test Topic",
                topic_content="Test Content",
                provider="OpenAI (ChatGPT)",
                api_key="",
                model_name="gpt-4o-mini",
            )
            self.assertFalse(res["success"])
            self.assertIn("OpenAI API Key is missing", res["error"])

    def test_grok_missing_key_error(self):
        from modules.ai_generator import generate_linkedin_post
        with patch.dict("os.environ", {"XAI_API_KEY": ""}, clear=True):
            res = generate_linkedin_post(
                topic_title="Test Topic",
                topic_content="Test Content",
                provider="xAI (Grok)",
                api_key="",
                model_name="grok-2-1212",
            )
            self.assertFalse(res["success"])
            self.assertIn("xAI (Grok) API Key is missing", res["error"])


class TestLinkedInAPI(unittest.TestCase):
    """Test LinkedIn API helpers."""

    def test_web_composer_url_generator(self):
        from modules.linkedin_api import generate_web_composer_url
        url = generate_web_composer_url("Post text", "https://arxiv.org/abs/1234")
        self.assertIn("https://www.linkedin.com/sharing/share-offsite/", url)
        self.assertIn("arxiv.org", url)

    def test_missing_access_token_handling(self):
        from modules.linkedin_api import get_linkedin_user_profile, publish_post_to_linkedin
        res = get_linkedin_user_profile("")
        self.assertFalse(res["success"])
        
        pub_res = publish_post_to_linkedin("", "Hello LinkedIn")
        self.assertFalse(pub_res["success"])


class TestTimeUtils(unittest.TestCase):
    """Test computer timezone synchronization and datetime formatting."""

    def test_timezone_resolution(self):
        from modules.time_utils import get_timezone, get_user_now, get_system_default_timezone
        tz_london = get_timezone("Europe/London")
        self.assertEqual(tz_london.key, "Europe/London")
        
        tz_ny = get_timezone("America/New_York")
        self.assertEqual(tz_ny.key, "America/New_York")

        # Invalid fallback should default to system timezone
        tz_fallback = get_timezone("Invalid/NonExistent_Zone")
        expected_sys = get_system_default_timezone()
        self.assertEqual(tz_fallback.key, expected_sys)

        now_london = get_user_now("Europe/London")
        self.assertEqual(now_london.tzinfo.key, "Europe/London")

    def test_user_dt_to_utc_and_back(self):
        from modules.time_utils import user_dt_to_utc_iso, utc_iso_to_user_dt, format_for_user
        
        # 10:00 AM in London (UTC+1 during BST)
        local_dt = datetime(2026, 8, 25, 10, 0, 0)
        utc_iso = user_dt_to_utc_iso(local_dt, "Europe/London")
        self.assertIn("09:00:00", utc_iso) # 09:00 UTC is 10:00 BST

        # Convert back
        recovered_dt = utc_iso_to_user_dt(utc_iso, "Europe/London")
        self.assertEqual(recovered_dt.hour, 10)
        self.assertEqual(recovered_dt.minute, 0)

        # Formatting
        formatted = format_for_user(utc_iso, "Europe/London")
        self.assertIn("10:00 AM", formatted)
        self.assertIn("Aug 25, 2026", formatted)

    def test_relative_countdown(self):
        from modules.time_utils import format_relative_countdown, user_dt_to_utc_iso, get_user_now
        
        user_now = get_user_now("Europe/London")
        future_dt = user_now + timedelta(hours=3, minutes=15)
        future_utc_iso = user_dt_to_utc_iso(future_dt, "Europe/London")
        
        countdown = format_relative_countdown(future_utc_iso, "Europe/London")
        self.assertIn("in 3h 1", countdown)


if __name__ == "__main__":
    unittest.main()
