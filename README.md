# ⚡ Daily LinkedIn AI Ghostwriter

A production-ready, local desktop web application built with **Streamlit**, supporting both **Google Gemini (`google-genai`)** and **OpenAI ChatGPT (`openai`)**, designed for Data Science and Software Engineering professionals.

It automatically pulls live tech and research news via RSS feeds, scrapes custom URLs, provides tailored engineering tone profiles, and crafts high-engagement LinkedIn posts with structured hooks, takeaways, and questions.

---

## 🌟 Key Features

1. **Multi-AI Engine (Google Gemini, OpenAI ChatGPT & xAI Grok)**:
   - **Google Gemini**: Official `google-genai` SDK with `gemini-3.7-flash`, `gemini-3.6-flash`, `gemini-3.5-flash`, `gemini-flash-latest`, Vertex AI support, and automatic fallback.
   - **OpenAI (ChatGPT)**: Full support for `gpt-4o`, `gpt-4o-mini`, `o3-mini`, `gpt-4-turbo`, and custom models via `openai` SDK.
   - **xAI (Grok)**: Support for `grok-2-1212`, `grok-beta`, `grok-2-vision-1212`, `grok-vision-beta`, and custom models via OpenAI client compatibility.
   - Structured Pydantic schema validation for deterministic post components across all models.


2. **Live Topic Discovery (RSS Engine)**:
   - Real-time aggregation from Hacker News, ArXiv CS/AI & ML research papers, TechCrunch AI, Dev.to Python, and VentureBeat.
   - Instant search and keyword filtering.
   - One-click post generation directly from any feed story.

3. **Custom Topic & Web Scraper**:
   - Paste any engineering blog URL, paper link, or company announcement for automated clean text extraction.
   - Write custom raw thoughts, architecture post-mortems, or code lessons.

4. **Engineered Personas & Tones**:
   - *Pragmatic Engineer* (systems design, production realities)
   - *Deep Technical Breakdown* (low-level mechanics, architecture, trade-offs)
   - *Building in Public / Founder* (milestones, lessons learned, metric updates)
   - *Contrarian Tech Insight* (challenging buzzwords, pragmatic realism)
   - *AI / Data Science Practitioner* (fine-tuning, RAG, latency/cost trade-offs)

5. **LinkedIn Post Studio & Simulator**:
   - Scroll-stopping Hook selector (switch between contrarian or data-driven openings).
   - Live editable post canvas with character count and word metrics.
   - Visual LinkedIn feed card simulator.
   - One-click copy helper.

6. **Direct LinkedIn Publishing & 1-Click Composer**:
   - **Direct REST API Publish**: 1-Click publish directly to your LinkedIn profile via LinkedIn Developer API (`w_member_social`).
   - **1-Click Web Composer**: Instant web intent button opening LinkedIn's composer in a new tab with zero setup.

7. **SQLite Storage & Archive Management**:
   - Save drafts locally into SQLite database (`data/ghostwriter.db`).
   - Star favorite posts, search history, update drafts, or delete old ones.
   - One-click export to **JSON** or consolidated **Markdown**.

---

## 🚀 Quickstart & 1-Click Execution

### ⚡ 1-Click Desktop Launchers (macOS)
Directly in your file manager / Finder, you have two 1-click double-clickable shortcuts:
1. **`Start_App.command`**: Double-click to start the server in the background and automatically open Google Chrome to your app.
2. **`Stop_App.command`**: Double-click to cleanly stop the server whenever you are done.

---

### Manual Terminal Setup:
```bash
cd "/Volumes/Ashraful_Drive/Code/Ai Tools/made_task_easy"
pip install -r requirements.txt
streamlit run app.py
```

The application will open automatically in your browser at `http://localhost:8501`.

---

## 📁 Project Structure

```
made_task_easy/
├── app.py                      # Streamlit UI & interactive workflow
├── modules/
│   ├── __init__.py
│   ├── ai_generator.py         # Google Gen AI SDK integration & structured schemas
│   ├── rss_service.py          # Curated RSS feed aggregation & search
│   ├── scraper_service.py      # Article extraction for custom URLs
│   └── storage.py              # SQLite persistence for drafts, stars & exports
├── data/                       # Local SQLite database directory (auto-created)
├── tests/
│   └── test_services.py        # Automated test suite
├── .env.example                # Sample environment file
├── requirements.txt            # Project dependencies
└── README.md                   # Documentation
```

---

## 🧪 Running Tests

To verify all components (RSS feeds, scraper, SQLite storage, schema validation):
```bash
python -m unittest tests/test_services.py
```
