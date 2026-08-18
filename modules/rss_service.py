"""
RSS Feed Aggregation and Topic Discovery Service.
Enriched with dedicated Programming, Architecture, Python, Web Dev, AI, and ArXiv Research channels.
"""

import html
import re
import time
from typing import Any, Dict, List, Optional
import feedparser
import requests

FEEDS_CATALOG: Dict[str, Dict[str, Any]] = {
    "⚡ All Categories": {
        "description": "Comprehensive stream across software engineering, architecture, AI, Python, web dev, and research.",
        "urls": [
            ("Hacker News Frontpage", "https://hnrss.org/frontpage", "General Tech"),
            ("Hacker News Programming", "https://hnrss.org/newest?q=programming+OR+architecture+OR+backend", "Engineering"),
            ("Hacker News AI/LLM", "https://hnrss.org/newest?q=AI+OR+LLM+OR+Python", "AI & ML"),
            ("InfoQ Architecture", "https://feed.infoq.com/", "Architecture"),
            ("The New Stack", "https://thenewstack.io/feed/", "Engineering"),
            ("FreeCodeCamp News", "https://www.freecodecamp.org/news/rss/", "Programming"),
            ("Dev.to Programming", "https://dev.to/feed/tag/programming", "Programming"),
            ("Dev.to Python", "https://dev.to/feed/tag/python", "Python"),
            ("Real Python", "https://realpython.com/atom.xml", "Python"),
            ("ArXiv Computer Science & AI", "https://export.arxiv.org/rss/cs.AI", "Research"),
            ("ArXiv Software Engineering", "https://export.arxiv.org/rss/cs.SE", "Research"),
            ("TechCrunch AI", "https://techcrunch.com/category/artificial-intelligence/feed/", "Industry News"),
            ("VentureBeat AI", "https://venturebeat.com/category/ai/feed/", "Industry News"),
        ],
    },
    "💻 Software Engineering & Architecture": {
        "description": "System design, microservices, backend engineering, cloud architecture, and clean code.",
        "urls": [
            ("InfoQ Architecture & Design", "https://feed.infoq.com/", "Architecture"),
            ("The New Stack", "https://thenewstack.io/feed/", "Engineering"),
            ("Hacker News Programming", "https://hnrss.org/newest?q=programming+OR+architecture+OR+backend+OR+database", "Engineering"),
            ("Dev.to System Architecture", "https://dev.to/feed/tag/architecture", "Architecture"),
            ("Dev.to Programming", "https://dev.to/feed/tag/programming", "Programming"),
            ("FreeCodeCamp Developer News", "https://www.freecodecamp.org/news/rss/", "Programming"),
            ("Dev.to DevOps & Cloud", "https://dev.to/feed/tag/devops", "DevOps"),
            ("ArXiv Software Engineering", "https://export.arxiv.org/rss/cs.SE", "Research"),
        ],
    },
    "🐍 Python & Data Engineering": {
        "description": "Python frameworks, FastAPI, Django, ETL pipelines, PyTorch, and data processing.",
        "urls": [
            ("Real Python Tutorials", "https://realpython.com/atom.xml", "Python"),
            ("Dev.to Python Community", "https://dev.to/feed/tag/python", "Python"),
            ("Hacker News Python & Data", "https://hnrss.org/newest?q=Python+OR+FastAPI+OR+Pandas+OR+Django", "Python"),
            ("Dev.to Data Engineering", "https://dev.to/feed/tag/dataengineering", "Data Eng"),
        ],
    },
    "🤖 AI, Machine Learning & LLMs": {
        "description": "Generative AI, foundation models, agents, prompt engineering, RAG, and neural architectures.",
        "urls": [
            ("Hacker News AI & LLM", "https://hnrss.org/newest?q=AI+OR+LLM+OR+OpenAI+OR+Claude+OR+Gemini", "AI & ML"),
            ("TechCrunch AI", "https://techcrunch.com/category/artificial-intelligence/feed/", "Industry News"),
            ("Dev.to Artificial Intelligence", "https://dev.to/feed/tag/ai", "AI & ML"),
            ("VentureBeat AI", "https://venturebeat.com/category/ai/feed/", "Industry News"),
        ],
    },
    "🔬 ArXiv & Research Papers": {
        "description": "State-of-the-art academic papers in AI, computer vision, NLP, and software systems.",
        "urls": [
            ("ArXiv AI", "https://export.arxiv.org/rss/cs.AI", "Research"),
            ("ArXiv Machine Learning", "https://export.arxiv.org/rss/cs.LG", "Research"),
            ("ArXiv Computation & Language (NLP)", "https://export.arxiv.org/rss/cs.CL", "Research"),
            ("ArXiv Software Engineering", "https://export.arxiv.org/rss/cs.SE", "Research"),
            ("ArXiv Distributed Computing", "https://export.arxiv.org/rss/cs.DC", "Research"),
        ],
    },
    "🌐 Web Development & Fullstack": {
        "description": "TypeScript, JavaScript, React, Next.js, Node.js, API design, and modern frontend tools.",
        "urls": [
            ("Dev.to Web Development", "https://dev.to/feed/tag/webdev", "Web Dev"),
            ("Dev.to JavaScript & TypeScript", "https://dev.to/feed/tag/javascript", "JavaScript"),
            ("Hacker News Fullstack", "https://hnrss.org/newest?q=React+OR+Typescript+OR+Nextjs+OR+Nodejs", "Web Dev"),
            ("FreeCodeCamp Web Dev", "https://www.freecodecamp.org/news/rss/", "Web Dev"),
        ],
    },
    "💼 Tech Industry & Startups": {
        "description": "Tech industry news, product launches, venture funding, and founder insights.",
        "urls": [
            ("Hacker News Frontpage", "https://hnrss.org/frontpage", "General Tech"),
            ("TechCrunch Startups", "https://techcrunch.com/category/startups/feed/", "Industry News"),
            ("VentureBeat Enterprise", "https://venturebeat.com/category/enterprise/feed/", "Industry News"),
        ],
    },
}


def clean_html_summary(raw_html: str) -> str:
    """Remove HTML tags and unescape text entities."""
    if not raw_html:
        return ""
    text = re.sub(r"<[^>]+>", " ", raw_html)
    text = html.unescape(text)
    text = re.sub(r"\s+", " ", text).strip()
    return text[:600] + ("..." if len(text) > 600 else "")


def fetch_single_feed(source_name: str, feed_url: str, category_tag: str, timeout: int = 8) -> List[Dict[str, Any]]:
    """Fetch and parse a single RSS feed safely with custom User-Agent headers."""
    items: List[Dict[str, Any]] = []
    headers = {
        "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36 LinkedInGhostwriter/2.0"
    }

    try:
        response = requests.get(feed_url, headers=headers, timeout=timeout)
        if response.status_code != 200:
            return items
        
        parsed = feedparser.parse(response.content)
        
        for entry in parsed.entries[:20]:
            title = entry.get("title", "").strip()
            link = entry.get("link", "").strip()
            summary_raw = entry.get("summary", "") or entry.get("description", "")
            clean_summary = clean_html_summary(summary_raw)
            published = entry.get("published", "") or entry.get("updated", "") or "Recent"

            if title and link:
                items.append({
                    "title": title,
                    "link": link,
                    "summary": clean_summary,
                    "published": published,
                    "source": source_name,
                    "category": category_tag,
                })
    except Exception as err:
        print(f"[RSS Service] Warning: Failed to fetch {source_name} ({feed_url}): {err}")
    
    return items


def get_feed_topics(
    category: str = "⚡ All Categories",
    search_keyword: Optional[str] = None,
    limit: int = 50,
) -> List[Dict[str, Any]]:
    """Fetch stories from the selected category, deduplicate, filter, and return up to limit."""
    category_config = FEEDS_CATALOG.get(category, FEEDS_CATALOG["⚡ All Categories"])
    all_articles: List[Dict[str, Any]] = []
    seen_titles = set()

    for source_name, feed_url, category_tag in category_config["urls"]:
        entries = fetch_single_feed(source_name, feed_url, category_tag)
        for item in entries:
            # Deduplicate by normalized title
            norm_title = re.sub(r"[^a-zA-Z0-9]", "", item["title"].lower())
            if norm_title and norm_title not in seen_titles:
                seen_titles.add(norm_title)
                all_articles.append(item)

    if search_keyword:
        kw = search_keyword.strip().lower()
        all_articles = [
            a for a in all_articles
            if kw in a["title"].lower() or kw in a["summary"].lower() or kw in a["source"].lower() or kw in a["category"].lower()
        ]

    return all_articles[:limit]
