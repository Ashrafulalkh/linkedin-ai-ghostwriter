"""
Automated Unit and Integration Tests for LinkedIn AI Ghostwriter.
"""

import json
import unittest
from unittest.mock import MagicMock, patch
from modules.storage import (
    init_db,
    save_draft,
    get_all_drafts,
    get_draft_by_id,
    update_draft,
    delete_draft,
    toggle_favorite,
    export_drafts_json,
    export_drafts_markdown,
)
from modules.rss_service import clean_html_summary, FEEDS_CATALOG, fetch_single_feed
from modules.scraper_service import scrape_article_content
from modules.ai_generator import LinkedInPostStructure, build_system_prompt, TONE_PROFILES


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



if __name__ == "__main__":
    unittest.main()
