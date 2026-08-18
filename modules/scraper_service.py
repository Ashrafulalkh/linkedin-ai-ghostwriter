"""
Web Scraper and Content Extractor for custom URLs and articles.
"""

import re
from typing import Any, Dict
from bs4 import BeautifulSoup
import requests


def scrape_article_content(url: str, timeout: int = 10) -> Dict[str, Any]:
    """
    Fetch and extract clean title, meta description, and body content from an article URL.
    """
    if not url or not (url.startswith("http://") or url.startswith("https://")):
        return {
            "success": False,
            "error": "Invalid URL format. Please include http:// or https://.",
            "title": "",
            "content": "",
            "url": url,
        }

    headers = {
        "User-Agent": (
            "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
            "AppleWebKit/537.36 (KHTML, like Gecko) "
            "Chrome/124.0.0.0 Safari/537.36"
        ),
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8",
        "Accept-Language": "en-US,en;q=0.5",
    }

    try:
        response = requests.get(url, headers=headers, timeout=timeout)
        if response.status_code != 200:
            return {
                "success": False,
                "error": f"Failed to retrieve page (HTTP Status Code: {response.status_code})",
                "title": "",
                "content": "",
                "url": url,
            }

        soup = BeautifulSoup(response.text, "html.parser")

        # Remove irrelevant non-content elements
        for element in soup(["script", "style", "nav", "header", "footer", "aside", "noscript", "svg"]):
            element.decompose()

        # Extract title
        title = ""
        og_title = soup.find("meta", property="og:title")
        if og_title and og_title.get("content"):
            title = str(og_title["content"]).strip()
        elif soup.title and soup.title.string:
            title = soup.title.string.strip()
        elif soup.find("h1"):
            title = soup.find("h1").get_text().strip()

        # Extract meta description
        meta_desc = ""
        og_desc = soup.find("meta", property="og:description")
        meta_d = soup.find("meta", attrs={"name": "description"})
        if og_desc and og_desc.get("content"):
            meta_desc = str(og_desc["content"]).strip()
        elif meta_d and meta_d.get("content"):
            meta_desc = str(meta_d["content"]).strip()

        # Extract main text paragraphs
        paragraphs = []
        # Look for typical article container first
        article_elem = soup.find("article") or soup.find("main") or soup.find("div", class_=re.compile(r"post|content|entry|article", re.I))
        search_root = article_elem if article_elem else soup

        for p in search_root.find_all(["p", "h2", "h3", "li"]):
            text = p.get_text().strip()
            # Filter out tiny boilerplate strings
            if len(text) > 30 and not any(skip in text.lower() for skip in ["cookie", "privacy policy", "subscribe", "all rights reserved"]):
                paragraphs.append(text)

        full_body = "\n\n".join(paragraphs)

        # Fallback if no structured paragraphs found
        if not full_body:
            full_body = soup.get_text(separator="\n", strip=True)
            # Clean up consecutive empty lines
            full_body = re.sub(r"\n{3,}", "\n\n", full_body)

        # Cap text length to avoid overflow
        clean_content = full_body[:4500].strip()

        return {
            "success": True,
            "title": title or "Extracted Article",
            "meta_description": meta_desc,
            "content": clean_content,
            "url": url,
            "error": None,
        }

    except requests.exceptions.Timeout:
        return {
            "success": False,
            "error": "Request timed out while trying to reach the article URL.",
            "title": "",
            "content": "",
            "url": url,
        }
    except Exception as e:
        return {
            "success": False,
            "error": f"Scraping error: {str(e)}",
            "title": "",
            "content": "",
            "url": url,
        }
