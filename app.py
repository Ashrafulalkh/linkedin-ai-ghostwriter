"""
Daily LinkedIn AI Ghostwriter - Desktop Web Application
Built with Streamlit and the Official Google Gen AI SDK (`google-genai`).
"""

import os
import urllib.parse
import streamlit as st
from dotenv import load_dotenv

# Load local environment variables
load_dotenv()

# Sync Streamlit Cloud secrets into os.environ for universal access (excluding personal user access tokens)
try:
    if hasattr(st, "secrets"):
        for k, v in st.secrets.items():
            if k != "LINKEDIN_ACCESS_TOKEN" and isinstance(v, (str, int, float, bool)):
                os.environ[k] = str(v)
except Exception:
    pass

DEFAULT_APP_URL = "https://linkedin-ai-ghostwriter-m86zum63j8lfura4uff6xs.streamlit.app"




from modules.ai_generator import (
    SUPPORTED_PROVIDERS,
    SUPPORTED_GEMINI_MODELS,
    SUPPORTED_OPENAI_MODELS,
    SUPPORTED_GROQ_MODELS,
    SUPPORTED_GROK_MODELS,
    SUPPORTED_MODELS,
    TONE_PROFILES,
    generate_linkedin_post,
    get_groq_available_models,
    regenerate_hooks,
)

from modules.linkedin_api import (
    exchange_authorization_code,
    generate_web_composer_url,
    get_linkedin_user_profile,
    publish_post_to_linkedin,
    save_access_token_to_env,
)
from modules.rss_service import FEEDS_CATALOG, get_feed_topics
from modules.scraper_service import scrape_article_content
from modules.storage import (
    delete_draft,
    export_drafts_json,
    export_drafts_markdown,
    get_all_drafts,
    init_db,
    save_draft,
    toggle_favorite,
    update_draft,
)

# Page configuration
st.set_page_config(
    page_title="LinkedIn AI Ghostwriter | Data Science & Engineering",
    page_icon="⚡",
    layout="wide",
    initial_sidebar_state="expanded",
)

# Initialize SQLite database
init_db()

# Handle incoming LinkedIn OAuth callback
if "code" in st.query_params:
    auth_code = st.query_params["code"]
    client_id = os.getenv("LINKEDIN_CLIENT_ID", "")
    client_secret = os.getenv("LINKEDIN_CLIENT_SECRET", "")
    redirect_uri_val = os.getenv("LINKEDIN_REDIRECT_URI", DEFAULT_APP_URL).rstrip("/")
    if client_id and client_secret:
        with st.spinner("Authenticating with LinkedIn..."):
            res = exchange_authorization_code(
                code=auth_code,
                client_id=client_id,
                client_secret=client_secret,
                redirect_uri=redirect_uri_val,
            )
            if res["success"]:
                st.session_state.linkedin_access_token = res["access_token"]
                # Auto fetch and store connected user profile in current session
                profile = get_linkedin_user_profile(res["access_token"])
                if profile.get("success"):
                    st.session_state.linkedin_profile = profile
                st.query_params.clear()
                st.success("🎉 LinkedIn Account Connected Successfully!")
                st.rerun()
            else:
                st.error(f"LinkedIn Connection Failed: {res['error']}")
                st.query_params.clear()

    else:
        st.error("LinkedIn Client ID or Client Secret is missing in Streamlit App Secrets / .env.")
        st.query_params.clear()



# Custom CSS for rich, modern UI/UX styling
st.markdown(
    """
    <style>
    /* Google Fonts */
    @import url('https://fonts.googleapis.com/css2?family=Plus+Jakarta+Sans:wght@300;400;500;600;700;800&family=JetBrains+Mono:wght@400;500;600&display=swap');
    
    html, body, [class*="css"], .stApp {
        font-family: 'Plus Jakarta Sans', -apple-system, BlinkMacSystemFont, sans-serif !important;
        letter-spacing: -0.01em;
    }
    
    code, pre, .stCode {
        font-family: 'JetBrains Mono', monospace !important;
    }

    /* Main Container Padding */
    .block-container {
        padding-top: 2rem !important;
        padding-bottom: 4rem !important;
        max-width: 1280px !important;
    }
    
    /* Hero Banner with Modern Mesh Gradient */
    .hero-container {
        background: linear-gradient(135deg, #091E3A 0%, #102A45 40%, #0052A3 80%, #0A66C2 100%);
        color: #ffffff;
        padding: 30px 36px;
        border-radius: 18px;
        margin-bottom: 26px;
        box-shadow: 0 10px 30px -5px rgba(10, 102, 194, 0.35), 0 0 0 1px rgba(255, 255, 255, 0.12) inset;
        position: relative;
        overflow: hidden;
    }
    .hero-container::before {
        content: '';
        position: absolute;
        top: -50%;
        right: -20%;
        width: 300px;
        height: 300px;
        background: radial-gradient(circle, rgba(0, 163, 255, 0.25) 0%, rgba(0,0,0,0) 70%);
        border-radius: 50%;
        pointer-events: none;
    }
    .hero-badge-row {
        display: flex;
        gap: 10px;
        margin-bottom: 12px;
        flex-wrap: wrap;
    }
    .hero-pill {
        display: inline-flex;
        align-items: center;
        gap: 6px;
        padding: 4px 12px;
        border-radius: 20px;
        font-size: 0.78rem;
        font-weight: 600;
        background: rgba(255, 255, 255, 0.15);
        backdrop-filter: blur(10px);
        border: 1px solid rgba(255, 255, 255, 0.2);
        color: #E0F2FE;
    }
    .hero-title {
        font-size: 2.1rem;
        font-weight: 800;
        margin: 0;
        letter-spacing: -0.8px;
        line-height: 1.2;
        background: linear-gradient(180deg, #FFFFFF 0%, #E2E8F0 100%);
        -webkit-background-clip: text;
        -webkit-text-fill-color: transparent;
    }
    .hero-subtitle {
        font-size: 1.02rem;
        color: #BAE6FD;
        margin-top: 8px;
        font-weight: 400;
        line-height: 1.5;
        max-width: 800px;
    }
    
    /* Feed Card Styling */
    .feed-card {
        background: rgba(255, 255, 255, 0.03);
        border: 1px solid rgba(140, 160, 190, 0.18);
        border-radius: 14px;
        padding: 22px 24px;
        margin-bottom: 16px;
        transition: all 0.25s cubic-bezier(0.16, 1, 0.3, 1);
        backdrop-filter: blur(8px);
        position: relative;
    }
    .feed-card:hover {
        border-color: #0A84FF;
        transform: translateY(-3px);
        box-shadow: 0 12px 28px rgba(0, 102, 255, 0.12), 0 0 0 1px rgba(10, 132, 255, 0.25);
    }
    
    /* Vibrant Tag Badges */
    .tag-badge {
        display: inline-block;
        padding: 4px 10px;
        border-radius: 12px;
        font-size: 0.74rem;
        font-weight: 700;
        text-transform: uppercase;
        letter-spacing: 0.5px;
        margin-right: 8px;
    }
    .tag-research { background: rgba(139, 92, 246, 0.18); color: #A78BFA; border: 1px solid rgba(139, 92, 246, 0.3); }
    .tag-ai { background: rgba(6, 182, 212, 0.18); color: #22D3EE; border: 1px solid rgba(6, 182, 212, 0.3); }
    .tag-general { background: rgba(16, 185, 129, 0.18); color: #34D399; border: 1px solid rgba(16, 185, 129, 0.3); }
    .tag-engineering { background: rgba(245, 158, 11, 0.18); color: #FBBF24; border: 1px solid rgba(245, 158, 11, 0.3); }
    .tag-industry { background: rgba(10, 102, 194, 0.18); color: #60A5FA; border: 1px solid rgba(10, 102, 194, 0.3); }
    
    .source-badge {
        display: inline-block;
        padding: 3px 10px;
        border-radius: 12px;
        font-size: 0.75rem;
        font-weight: 500;
        background: rgba(120, 140, 170, 0.12);
        color: #94A3B8;
        border: 1px solid rgba(120, 140, 170, 0.2);
    }
    
    /* Hook Cards in Studio */
    .hook-card {
        background: rgba(10, 102, 194, 0.06);
        border: 1px solid rgba(10, 102, 194, 0.22);
        border-left: 4px solid #0A66C2;
        border-radius: 10px;
        padding: 14px 16px;
        margin-bottom: 12px;
        font-size: 0.92rem;
        line-height: 1.5;
    }

    /* LinkedIn Post Preview Mockup */
    .linkedin-mockup {
        background: #ffffff;
        color: #191919;
        border: 1px solid #e2e8f0;
        border-radius: 14px;
        padding: 22px 24px;
        box-shadow: 0 4px 20px -2px rgba(0,0,0,0.08), 0 0 1px rgba(0,0,0,0.05);
        margin-top: 8px;
    }
    .linkedin-header {
        display: flex;
        align-items: center;
        margin-bottom: 16px;
    }
    .avatar-circle {
        width: 50px;
        height: 50px;
        border-radius: 50%;
        background: linear-gradient(135deg, #0A66C2 0%, #004182 100%);
        color: white;
        display: flex;
        align-items: center;
        justify-content: center;
        font-weight: 700;
        font-size: 1.15rem;
        margin-right: 14px;
        box-shadow: 0 2px 8px rgba(10, 102, 194, 0.3);
    }
    .author-name {
        font-weight: 700;
        font-size: 0.98rem;
        color: #0f172a;
        margin: 0;
        display: flex;
        align-items: center;
        gap: 6px;
    }
    .author-title {
        font-size: 0.82rem;
        color: #64748b;
        margin: 2px 0 0 0;
    }
    .author-time {
        font-size: 0.76rem;
        color: #94a3b8;
        display: flex;
        align-items: center;
        gap: 4px;
        margin-top: 2px;
    }
    .post-content-preview {
        font-size: 0.96rem;
        line-height: 1.62;
        white-space: pre-wrap;
        color: #1e293b;
        font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif;
        margin: 14px 0 18px 0;
        word-break: break-word;
    }
    .linkedin-reactions-bar {
        display: flex;
        justify-content: space-between;
        align-items: center;
        padding-bottom: 10px;
        border-bottom: 1px solid #f1f5f9;
        font-size: 0.82rem;
        color: #64748b;
    }
    .reaction-icons {
        display: inline-flex;
        align-items: center;
        gap: 2px;
        margin-right: 6px;
    }
    .linkedin-footer {
        padding-top: 10px;
        display: flex;
        justify-content: space-around;
        color: #475569;
        font-size: 0.88rem;
        font-weight: 600;
    }
    .linkedin-footer span {
        display: flex;
        align-items: center;
        gap: 6px;
        cursor: pointer;
        padding: 6px 12px;
        border-radius: 6px;
        transition: background 0.15s;
    }
    .linkedin-footer span:hover {
        background: #f1f5f9;
        color: #0A66C2;
    }

    /* Pulse Indicator */
    .pulse-dot {
        width: 8px;
        height: 8px;
        border-radius: 50%;
        background: #22C55E;
        box-shadow: 0 0 0 0 rgba(34, 197, 94, 0.7);
        animation: pulse 1.8s infinite;
        display: inline-block;
    }
    @keyframes pulse {
        0% { transform: scale(0.95); box-shadow: 0 0 0 0 rgba(34, 197, 94, 0.7); }
        70% { transform: scale(1); box-shadow: 0 0 0 6px rgba(34, 197, 94, 0); }
        100% { transform: scale(0.95); box-shadow: 0 0 0 0 rgba(34, 197, 94, 0); }
    }
    </style>
    """,
    unsafe_allow_html=True,
)

# Initialize Session State
if "selected_story" not in st.session_state:
    st.session_state.selected_story = None
if "generated_post" not in st.session_state:
    st.session_state.generated_post = None
if "current_editor_content" not in st.session_state:
    st.session_state.current_editor_content = ""
if "post_editor_textarea" not in st.session_state:
    st.session_state.post_editor_textarea = ""
if "active_tab_index" not in st.session_state:
    st.session_state.active_tab_index = 0
if "custom_scraped_data" not in st.session_state:
    st.session_state.custom_scraped_data = None
if "copy_status" not in st.session_state:
    st.session_state.copy_status = False
if "feed_limit" not in st.session_state:
    st.session_state.feed_limit = 15


def set_editor_content(text: str):
    """Safely updates both session state tracking and the text area widget key."""
    st.session_state.current_editor_content = text
    st.session_state.post_editor_textarea = text


# ==========================================
# SIDEBAR: CONFIGURATION & SETTINGS
# ==========================================
with st.sidebar:
    st.markdown("### ⚡ AI Provider & Model")
    
    provider_choice = st.radio(
        "Select AI Provider",
        options=SUPPORTED_PROVIDERS,
        horizontal=True,
        help="Choose between Google Gemini, OpenAI (ChatGPT), Groq (Ultra-Fast), or xAI (Grok).",
    )

    if provider_choice == "Google Gemini":
        env_gemini_key = os.getenv("GEMINI_API_KEY", "")
        api_key_input = st.text_input(
            "Gemini API Key",
            value=env_gemini_key,
            type="password",
            help="Reads automatically from .env or paste your Google AI Studio API key.",
        )
        if api_key_input:
            st.success("Gemini API Key configured", icon="✅")
        else:
            st.warning("Gemini API Key needed", icon="⚠️")
            st.caption("[Get a free Gemini API Key](https://aistudio.google.com/)")

        model_options = SUPPORTED_GEMINI_MODELS + ["Custom Model..."]
        selected_model_choice = st.selectbox(
            "Gemini Model",
            options=model_options,
            index=0,
            help="gemini-3.7-flash and gemini-3.6-flash provide state-of-the-art reasoning and speed.",
        )
        if selected_model_choice == "Custom Model...":
            selected_model = st.text_input("Custom Model Name", value="gemini-3.7-flash")
        else:
            selected_model = selected_model_choice

    elif provider_choice == "OpenAI (ChatGPT)":
        env_openai_key = os.getenv("OPENAI_API_KEY", "")
        api_key_input = st.text_input(
            "OpenAI API Key",
            value=env_openai_key,
            type="password",
            help="Reads automatically from .env or paste your OpenAI API key.",
        )
        if api_key_input:
            st.success("OpenAI API Key configured", icon="✅")
        else:
            st.warning("OpenAI API Key needed", icon="⚠️")
            st.caption("[Get an OpenAI API Key](https://platform.openai.com/api-keys)")

        model_options = SUPPORTED_OPENAI_MODELS + ["Custom Model..."]
        selected_model_choice = st.selectbox(
            "ChatGPT / OpenAI Model",
            options=model_options,
            index=0,
            help="gpt-4o and gpt-4o-mini offer top quality and fast generation.",
        )
        if selected_model_choice == "Custom Model...":
            selected_model = st.text_input("Custom Model Name", value="gpt-4o")
        else:
            selected_model = selected_model_choice

    elif provider_choice == "Groq":
        env_groq_key = os.getenv("GROQ_API_KEY", "")
        api_key_input = st.text_input(
            "Groq API Key",
            value=env_groq_key,
            type="password",
            help="Reads automatically from .env or paste your Groq API key (starts with gsk_).",
        )
        if api_key_input:
            st.success("Groq API Key configured", icon="⚡")
        else:
            st.warning("Groq API Key needed", icon="⚠️")
            st.caption("[Get a free Groq API Key](https://console.groq.com/keys)")

        available_groq_models = get_groq_available_models(api_key_input)
        model_options = available_groq_models + ["Custom Model..."]
        selected_model_choice = st.selectbox(
            "Groq Model",
            options=model_options,
            index=0,
            help="High-speed open models hosted on Groq LPU inference engine.",
        )
        if selected_model_choice == "Custom Model...":
            default_val = available_groq_models[0] if available_groq_models else "openai/gpt-oss-120b"
            selected_model = st.text_input("Custom Model Name", value=default_val)
        else:
            selected_model = selected_model_choice

    else:
        # xAI (Grok)
        env_grok_key = os.getenv("XAI_API_KEY", "")
        api_key_input = st.text_input(
            "xAI (Grok) API Key",
            value=env_grok_key,
            type="password",
            help="Reads automatically from .env or paste your xAI API key.",
        )
        if api_key_input:
            st.success("xAI Grok API Key configured", icon="✅")
        else:
            st.warning("xAI Grok API Key needed", icon="⚠️")
            st.caption("[Get an xAI API Key](https://console.x.ai/)")

        model_options = SUPPORTED_GROK_MODELS + ["Custom Model..."]
        selected_model_choice = st.selectbox(
            "xAI Grok Model",
            options=model_options,
            index=0,
            help="grok-4.6, grok-4.5, grok-4.3, grok-4, and grok-3 provide state-of-the-art reasoning and code intelligence.",
        )
        if selected_model_choice == "Custom Model...":
            selected_model = st.text_input("Custom Model Name", value="grok-4.6")
        else:
            selected_model = selected_model_choice



    st.divider()

    
    selected_tone = st.selectbox(
        "Ghostwriter Tone",
        options=list(TONE_PROFILES.keys()),
        index=0,
        help="Select the perspective and voice for the LinkedIn post.",
    )
    st.caption(f"_{TONE_PROFILES[selected_tone]['description']}_")
    
    user_persona = st.text_input(
        "Your Professional Persona",
        value="Principal Engineer / AI & Data Science Lead",
        help="Tailors technical vocabulary, context, and seniority.",
    )

    post_length = st.select_slider(
        "Post Length",
        options=["Concise (~120 words)", "Medium (150-250 words)", "In-Depth (250-400 words)"],
        value="Medium (150-250 words)",
    )

    temperature = st.slider(
        "Creativity (Temperature)",
        min_value=0.2,
        max_value=1.0,
        value=0.7,
        step=0.1,
        help="Higher values give more creative/opinionated takes, lower values are more analytical.",
    )

    st.divider()
    
    # Quick Statistics
    all_drafts = get_all_drafts()
    fav_count = sum(1 for d in all_drafts if d.get("is_favorite") == 1)
    st.markdown(f"**📊 Library Stats:**")
    st.markdown(f"- 📁 Total Drafts Saved: **{len(all_drafts)}**")
    st.markdown(f"- ⭐ Starred Posts: **{fav_count}**")

    st.divider()

    # LinkedIn Account Integration
    st.markdown("### 🔗 LinkedIn Direct Posting")
    client_id_val = os.getenv("LINKEDIN_CLIENT_ID", "")
    session_linkedin_token = st.session_state.get("linkedin_access_token", "")
    session_profile = st.session_state.get("linkedin_profile")
    redirect_uri_val = os.getenv("LINKEDIN_REDIRECT_URI", DEFAULT_APP_URL).rstrip("/")
    encoded_redirect = urllib.parse.quote(redirect_uri_val, safe="")

    if session_linkedin_token:
        profile_name = session_profile.get("name", "Connected User") if session_profile else "LinkedIn User"
        st.success(f"✅ Connected as **{profile_name}**", icon="👤")
        if st.button("🚪 Disconnect LinkedIn", use_container_width=True):
            st.session_state.linkedin_access_token = ""
            st.session_state.linkedin_profile = None
            st.rerun()
        linkedin_token_input = session_linkedin_token
    else:
        # 1-Click OAuth Connect Button
        if client_id_val:
            auth_url = (
                f"https://www.linkedin.com/oauth/v2/authorization?"
                f"response_type=code&client_id={client_id_val}&redirect_uri={encoded_redirect}&"
                f"scope=w_member_social%20openid%20profile%20email&state=ghostwriter"
            )
            st.link_button("🔗 1-Click Connect LinkedIn", url=auth_url, use_container_width=True)
        else:
            st.caption("ℹ️ Configure `LINKEDIN_CLIENT_ID` and `LINKEDIN_CLIENT_SECRET` in Streamlit Secrets to enable 1-Click OAuth.")

        linkedin_token_input = st.text_input(
            "Or Paste Access Token Manually",
            value="",
            type="password",
            help="Your token is private and only stored in this browser tab.",
        )

        if linkedin_token_input:
            if st.button("🔍 Verify LinkedIn Account", use_container_width=True):
                with st.spinner("Connecting to LinkedIn..."):
                    profile = get_linkedin_user_profile(linkedin_token_input)
                    if profile["success"]:
                        st.session_state.linkedin_access_token = linkedin_token_input
                        st.session_state.linkedin_profile = profile
                        st.success(f"Connected as **{profile['name']}**!")
                        st.rerun()
                    else:
                        st.error(profile["error"])
    
    env_linkedin_urn = os.getenv("LINKEDIN_AUTHOR_URN", "")
    linkedin_urn_input = st.text_input(
        "LinkedIn Member URN (Optional)",
        value=env_linkedin_urn,
        placeholder="urn:li:person:YOUR_ID or leave blank for auto-detect",
        help="Optional: Only needed if your token has 'w_member_social' without 'openid/profile'.",
    )


    
    with st.expander("ℹ️ Redirect URI Configuration"):
        st.markdown(
            f"""
            In your **[LinkedIn Developer Portal](https://developer.linkedin.com/)** -> Your App -> **Auth** tab:
            
            Under **"Authorized redirect URLs for your app"**, make sure you add:
            - `{redirect_uri_val}`
            - `http://localhost:8501` (for local development)
            """
        )





# ==========================================
# HERO BANNER
# ==========================================
st.markdown(
    """
    <div class="hero-container">
        <div class="hero-badge-row">
            <span class="hero-pill"><span class="pulse-dot"></span> LinkedIn API Ready</span>
            <span class="hero-pill">⚡ Gemini 3.7 & ChatGPT (GPT-4o) Engine</span>
            <span class="hero-pill">📡 Live ArXiv & HackerNews Stream</span>
        </div>
        <div class="hero-title">⚡ Daily LinkedIn AI Ghostwriter</div>
        <div class="hero-subtitle">
            Curate live tech breakthroughs, architectural lessons, and research into high-signal LinkedIn posts tailored for Data Science & Software Engineering leaders.
        </div>
    </div>
    """,
    unsafe_allow_html=True,
)

# Tabs Navigation
tab_rss, tab_custom, tab_studio, tab_history = st.tabs([
    "📡 Live Topic Discovery",
    "✍️ Custom Topic / URL Extractor",
    "🛠️ LinkedIn Post Studio",
    "🗄️ Saved Drafts & History",
])


# ==========================================
# TAB 1: LIVE TOPIC DISCOVERY (RSS)
# ==========================================
with tab_rss:
    st.subheader("Explore Trending Tech, Code & Research")
    st.caption("Live stream from InfoQ, The New Stack, Real Python, ArXiv, Hacker News, FreeCodeCamp, and Dev.to.")

    col1, col2, col3, col4 = st.columns([3.2, 2.8, 1.4, 1.4])
    with col1:
        category_choice = st.selectbox(
            "Category",
            options=list(FEEDS_CATALOG.keys()),
            index=0,
            label_visibility="collapsed",
        )
    with col2:
        search_kw = st.text_input(
            "Filter topics...",
            placeholder="Search keywords (e.g. FastAPI, RAG, Rust, K8s)",
            label_visibility="collapsed",
        )
    with col3:
        if st.button("🔥 Latest News", use_container_width=True, help="Reset to latest 15 fresh stories"):
            st.session_state.feed_limit = 15
            st.rerun()
    with col4:
        if st.button("🔄 Refresh", use_container_width=True):
            st.rerun()

    # Active Limit
    active_limit = st.session_state.get("feed_limit", 15)

    with st.spinner(f"Fetching {active_limit} live stories from {category_choice}..."):
        topics = get_feed_topics(category=category_choice, search_keyword=search_kw, limit=active_limit)

    if not topics:
        st.info("No matching stories found. Try a different keyword or category.")
    else:
        st.markdown(f"Showing **{len(topics)}** live topics from **{category_choice}**:")
        for idx, story in enumerate(topics):
            # Dynamic tag class based on category
            cat_lower = story['category'].lower()
            if "research" in cat_lower or "arxiv" in cat_lower:
                tag_class = "tag-research"
            elif "ai" in cat_lower or "ml" in cat_lower:
                tag_class = "tag-ai"
            elif "python" in cat_lower:
                tag_class = "tag-engineering"
            elif "architecture" in cat_lower or "engineering" in cat_lower or "devops" in cat_lower or "programming" in cat_lower:
                tag_class = "tag-engineering"
            elif "web" in cat_lower or "javascript" in cat_lower:
                tag_class = "tag-general"
            elif "industry" in cat_lower or "news" in cat_lower:
                tag_class = "tag-industry"
            else:
                tag_class = "tag-general"

            with st.container():
                st.markdown(
                    f"""
                    <div class="feed-card">
                        <div style="display:flex; justify-content:space-between; align-items:center; margin-bottom:8px;">
                            <div>
                                <span class="tag-badge {tag_class}">{story['category']}</span>
                                <span class="source-badge">🌐 {story['source']}</span>
                            </div>
                            <span style="font-size:0.78rem; color:#94A3B8;">🕒 {story['published']}</span>
                        </div>
                        <h4 style="margin: 6px 0 8px 0; font-size:1.08rem; font-weight:700;">
                            <a href="{story['link']}" target="_blank" style="text-decoration:none; color:inherit;">
                                {story['title']} <span style="font-size:0.85rem; opacity:0.7;">↗</span>
                            </a>
                        </h4>
                        <p style="font-size:0.92rem; margin-bottom:6px; opacity:0.85; line-height:1.55;">
                            {story['summary']}
                        </p>
                    </div>
                    """,
                    unsafe_allow_html=True,
                )
                
                btn_col1, btn_col2, _ = st.columns([2, 2, 6])
                with btn_col1:
                    if st.button("⚡ Craft LinkedIn Post", key=f"btn_craft_{idx}", type="primary", use_container_width=True):
                        st.session_state.selected_story = {
                            "title": story["title"],
                            "content": story["summary"],
                            "url": story["link"],
                            "source": story["source"],
                        }
                        
                        # Generate post immediately
                        if not api_key_input:
                            st.error(f"Please configure your {provider_choice} API Key in the sidebar first!")
                        else:
                            with st.spinner(f"Generating high-signal post with {provider_choice} ({selected_model})..."):
                                result = generate_linkedin_post(
                                    topic_title=story["title"],
                                    topic_content=story["summary"],
                                    tone=selected_tone,
                                    persona=user_persona,
                                    target_length=post_length,
                                    model_name=selected_model,
                                    api_key=api_key_input,
                                    temperature=temperature,
                                    provider=provider_choice,
                                )
                                if result["success"]:
                                    st.session_state.generated_post = result["data"]
                                    set_editor_content(result["data"]["full_assembled_post"])
                                    st.success(f"Post generated with `{result.get('model_used', selected_model)}`! Navigate to 'LinkedIn Post Studio' tab to edit & copy.")
                                else:
                                    st.error(result["error"])
                with btn_col2:
                    if st.button("🔍 Scrape Full Article", key=f"btn_scrape_{idx}", use_container_width=True):
                        with st.spinner("Scraping full article text..."):
                            scraped = scrape_article_content(story["link"])
                            if scraped["success"]:
                                st.session_state.selected_story = {
                                    "title": scraped["title"] or story["title"],
                                    "content": scraped["content"],
                                    "url": story["link"],
                                    "source": story["source"],
                                }
                                st.success(f"Extracted {len(scraped['content'])} characters from article! Switch to Studio to generate.")
                            else:
                                st.error(scraped["error"])
                st.markdown("<div style='margin-bottom:12px;'></div>", unsafe_allow_html=True)

        # Pagination & Load More Controls at the Bottom
        st.markdown("<hr style='margin: 24px 0 16px 0;'>", unsafe_allow_html=True)
        bot_col1, bot_col2, bot_col3 = st.columns([2.5, 2, 1.5])
        
        with bot_col1:
            if st.button("⚡ Show More Stories (+15 Topics)", type="primary", use_container_width=True):
                st.session_state.feed_limit = active_limit + 15
                st.rerun()
                
        with bot_col2:
            if st.button("🔥 Load 50 Latest Topics", use_container_width=True):
                st.session_state.feed_limit = 50
                st.rerun()
                
        with bot_col3:
            if st.button("⏪ Reset to Top 15", use_container_width=True):
                st.session_state.feed_limit = 15
                st.rerun()



# ==========================================
# TAB 2: CUSTOM TOPIC & URL EXTRACTOR
# ==========================================
with tab_custom:
    st.subheader("Draft from Your Own Ideas or Any URL")
    st.caption("Paste a link to any blog, paper, or company engineering post, or write your own raw notes.")

    input_mode = st.radio(
        "Input Mode",
        ["🔗 Paste Article / Blog URL", "📝 Custom Raw Notes / Project Update"],
        horizontal=True,
    )

    if "URL" in input_mode:
        custom_url = st.text_input(
            "Article / Paper URL",
            placeholder="https://engineering.atspotify.com/... or https://arxiv.org/abs/...",
        )
        col_scrape, col_clear = st.columns([2, 1])
        with col_scrape:
            if st.button("📥 Fetch & Extract Article", use_container_width=True):
                if not custom_url:
                    st.warning("Please enter a valid URL.")
                else:
                    with st.spinner("Extracting content from page..."):
                        scraped = scrape_article_content(custom_url)
                        if scraped["success"]:
                            st.session_state.custom_scraped_data = scraped
                            st.success(f"Successfully extracted: **{scraped['title']}**")
                        else:
                            st.error(scraped["error"])
        
        if st.session_state.custom_scraped_data:
            s_data = st.session_state.custom_scraped_data
            custom_title = st.text_input("Article Title", value=s_data["title"])
            custom_content = st.text_area("Extracted Body Content", value=s_data["content"], height=200)
            custom_notes = st.text_input("Your Specific Angle / Key Takeaway (Optional)", placeholder="e.g. Highlight why this matters for distributed systems teams")
            
            if st.button("🚀 Generate LinkedIn Post from URL", type="primary", use_container_width=True):
                if not api_key_input:
                    st.error(f"Please configure your {provider_choice} API Key in the sidebar!")
                else:
                    with st.spinner(f"Generating post with {provider_choice} ({selected_model})..."):
                        res = generate_linkedin_post(
                            topic_title=custom_title,
                            topic_content=custom_content,
                            tone=selected_tone,
                            persona=user_persona,
                            custom_notes=custom_notes,
                            target_length=post_length,
                            model_name=selected_model,
                            api_key=api_key_input,
                            temperature=temperature,
                            provider=provider_choice,
                        )
                        if res["success"]:
                            st.session_state.selected_story = {
                                "title": custom_title,
                                "content": custom_content,
                                "url": s_data.get("url", ""),
                                "source": "Custom URL",
                            }
                            st.session_state.generated_post = res["data"]
                            set_editor_content(res["data"]["full_assembled_post"])
                            st.success(f"Generated with `{res.get('model_used', selected_model)}`! Head over to the 'LinkedIn Post Studio' tab to refine.")
                        else:
                            st.error(res["error"])
    else:
        # Custom thoughts
        custom_topic_title = st.text_input("Topic / Headline", placeholder="e.g., Why we migrated our Python microservice from sync to async")
        custom_topic_notes = st.text_area(
            "Core Thoughts, Code snippet context, or Architecture lessons",
            placeholder="Bullet points of what you built, what broke in production, latency metrics before/after, lessons learned...",
            height=220,
        )
        custom_angle = st.text_input("Core Takeaway / CTA focus", placeholder="e.g. Focus on database connection pooling bottleneck")

        if st.button("🚀 Generate LinkedIn Post", type="primary", use_container_width=True):
            if not custom_topic_title and not custom_topic_notes:
                st.warning("Please provide a topic title or notes.")
            elif not api_key_input:
                st.error(f"Please configure your {provider_choice} API Key in the sidebar!")
            else:
                with st.spinner(f"Crafting post with {provider_choice} ({selected_model})..."):
                    res = generate_linkedin_post(
                        topic_title=custom_topic_title or "Technical Insight",
                        topic_content=custom_topic_notes,
                        tone=selected_tone,
                        persona=user_persona,
                        custom_notes=custom_angle,
                        target_length=post_length,
                        model_name=selected_model,
                        api_key=api_key_input,
                        temperature=temperature,
                        provider=provider_choice,
                    )
                    if res["success"]:
                        st.session_state.selected_story = {
                            "title": custom_topic_title or "Custom Post",
                            "content": custom_topic_notes,
                            "url": "",
                            "source": "Manual Input",
                        }
                        st.session_state.generated_post = res["data"]
                        set_editor_content(res["data"]["full_assembled_post"])
                        st.success(f"Post crafted with `{res.get('model_used', selected_model)}`! Switch to 'LinkedIn Post Studio' tab to edit and copy.")
                    else:
                        st.error(res["error"])


# ==========================================
# TAB 3: LINKEDIN POST STUDIO & PREVIEW
# ==========================================
with tab_studio:
    st.subheader("Post Editor & LinkedIn Simulator")
    
    # Active LinkedIn status banner
    if session_linkedin_token or linkedin_token_input:
        st.success("🟢 **LinkedIn Connected** — Ready to publish directly to your feed!", icon="🚀")
    else:
        st.info("💡 Tip: Connect your LinkedIn in the sidebar to publish directly with 1 click, or use the Web Composer.")


    gen_data = st.session_state.generated_post or {}
    
    # Top bar: Hooks variation selector if available
    if gen_data and "hook_option_1" in gen_data:
        with st.expander("🎣 Hook Alternatives & Openings (Click to Test)", expanded=True):
            col_h1, col_h2 = st.columns(2)
            with col_h1:
                st.markdown(
                    f"""
                    <div class="hook-card">
                        <div style="font-weight:700; color:#0A66C2; margin-bottom:4px;">🔥 Hook Option 1 (Contrarian / Curiosity)</div>
                        <div>{gen_data.get('hook_option_1', '')}</div>
                    </div>
                    """,
                    unsafe_allow_html=True,
                )
                if st.button("Apply Hook 1 to Editor", key="apply_hook_1", use_container_width=True):
                    body_part = gen_data.get("body", "")
                    takeaway_part = f"\n\nTakeaway: {gen_data.get('technical_takeaway', '')}"
                    q_part = f"\n\n{gen_data.get('discussion_question', '')}"
                    tags_part = f"\n\n{' '.join(gen_data.get('hashtags', []))}"
                    new_assembled = f"{gen_data.get('hook_option_1')}\n\n{body_part}{takeaway_part}{q_part}{tags_part}"
                    set_editor_content(new_assembled)
                    st.rerun()

            with col_h2:
                st.markdown(
                    f"""
                    <div class="hook-card">
                        <div style="font-weight:700; color:#0A66C2; margin-bottom:4px;">📊 Hook Option 2 (Data-Driven / Insight)</div>
                        <div>{gen_data.get('hook_option_2', '')}</div>
                    </div>
                    """,
                    unsafe_allow_html=True,
                )
                if st.button("Apply Hook 2 to Editor", key="apply_hook_2", use_container_width=True):
                    body_part = gen_data.get("body", "")
                    takeaway_part = f"\n\nTakeaway: {gen_data.get('technical_takeaway', '')}"
                    q_part = f"\n\n{gen_data.get('discussion_question', '')}"
                    tags_part = f"\n\n{' '.join(gen_data.get('hashtags', []))}"
                    new_assembled = f"{gen_data.get('hook_option_2')}\n\n{body_part}{takeaway_part}{q_part}{tags_part}"
                    set_editor_content(new_assembled)
                    st.rerun()

    # Two-column layout: Left Editor, Right LinkedIn Feed Mockup
    col_editor, col_preview = st.columns([1.1, 0.9], gap="large")

    with col_editor:
        st.markdown("#### ✏️ Live Post Editor")
        
        # Ensure post_editor_textarea is synchronized with current_editor_content
        if "post_editor_textarea" not in st.session_state or (not st.session_state.post_editor_textarea and st.session_state.current_editor_content):
            st.session_state.post_editor_textarea = st.session_state.current_editor_content

        edited_text = st.text_area(
            "Edit Post Content",
            placeholder="Type, edit, or paste your LinkedIn post here, or craft one from Tab 1 / Tab 2...",
            height=360,
            label_visibility="collapsed",
            key="post_editor_textarea",
        )
        # Sync edited text
        st.session_state.current_editor_content = edited_text

        # Metrics
        char_count = len(edited_text)
        word_count = len(edited_text.split())
        st.caption(f"📏 **{char_count}** characters | **{word_count}** words (Recommended: 800–1800 chars for optimal reach)")

        # Action Buttons Row
        btn_c1, btn_c2, btn_c3 = st.columns([1.2, 1.2, 1])
        
        with btn_c1:
            if st.button("💾 Save as Draft", use_container_width=True):
                if not edited_text.strip():
                    st.warning("Please write or generate some content first.")
                else:
                    story_info = st.session_state.selected_story or {}
                    draft_title = story_info.get("title", edited_text.split("\n")[0][:60])
                    d_id = save_draft(
                        title=draft_title,
                        full_content=edited_text,
                        source_type=story_info.get("source", "Custom"),
                        source_url=story_info.get("url", ""),
                        source_title=story_info.get("title", ""),
                        tone=selected_tone,
                        persona=user_persona,
                        hooks=[gen_data.get("hook_option_1", ""), gen_data.get("hook_option_2", "")],
                        body=gen_data.get("body", ""),
                        takeaway=gen_data.get("technical_takeaway", ""),
                        question=gen_data.get("discussion_question", ""),
                        hashtags=" ".join(gen_data.get("hashtags", [])),
                    )
                    st.success(f"Draft #{d_id} saved to SQLite database!")

        with btn_c2:
            st.code(edited_text, language="markdown")
            st.caption("Click top-right icon above for 1-click clipboard copy.")

        with btn_c3:
            if st.button("✨ Regenerate", use_container_width=True):
                story_info = st.session_state.selected_story or {}
                if not story_info.get("title"):
                    st.warning("No base topic found to regenerate. Generate from Tab 1 or Tab 2 first.")
                elif not api_key_input:
                    st.error(f"Please configure your {provider_choice} API Key in the sidebar!")
                else:
                    with st.spinner(f"Regenerating new angle with {provider_choice} ({selected_model})..."):
                        res = generate_linkedin_post(
                            topic_title=story_info.get("title", ""),
                            topic_content=story_info.get("content", ""),
                            tone=selected_tone,
                            persona=user_persona,
                            target_length=post_length,
                            model_name=selected_model,
                            api_key=api_key_input,
                            temperature=temperature + 0.1 if temperature < 0.9 else 0.8,
                            provider=provider_choice,
                        )
                        if res["success"]:
                            st.session_state.generated_post = res["data"]
                            set_editor_content(res["data"]["full_assembled_post"])
                            st.rerun()

        # Dedicated LinkedIn Publishing Section
        st.markdown("---")
        st.markdown("### 🚀 Publish to LinkedIn")
        pub_col1, pub_col2 = st.columns([1.2, 1.2])

        with pub_col1:
            active_token = linkedin_token_input or session_linkedin_token
            # Direct API Publishing Button

            if st.button("🚀 Publish Directly to My LinkedIn Feed", type="primary", use_container_width=True):
                if not edited_text.strip():
                    st.warning("Cannot publish an empty post! Please type or generate a post first.")
                elif not active_token:
                    st.warning("Please connect your LinkedIn account in the sidebar first!")
                else:
                    with st.spinner("Publishing post directly to LinkedIn..."):
                        story_info = st.session_state.selected_story or {}
                        pub_res = publish_post_to_linkedin(
                            access_token=active_token,
                            text_content=edited_text,
                            author_urn=linkedin_urn_input if linkedin_urn_input else None,
                            article_url=story_info.get("url"),
                        )
                        if pub_res["success"]:
                            st.balloons()
                            post_url = pub_res.get("post_url", "https://www.linkedin.com/feed/")
                            st.success(f"🎉 Post published successfully to LinkedIn!")
                            st.markdown(f"👉 **[View your live post on LinkedIn ↗]({post_url})**")
                        else:
                            st.error(pub_res["error"])

        with pub_col2:
            story_info = st.session_state.selected_story or {}
            article_link = story_info.get("url") if story_info else None
            composer_url = generate_web_composer_url(edited_text, article_link)
            st.link_button(
                "🌐 Open in LinkedIn Web Composer (0 Setup)",
                url=composer_url,
                use_container_width=True,
                help="Opens LinkedIn with your draft ready to publish in 1 click.",
            )

    with col_preview:
        st.markdown("#### 📱 LinkedIn Feed Preview")
        clean_display_text = edited_text if edited_text else "Your post preview will appear here..."
        
        # Ultra-realistic HTML Mockup of LinkedIn feed
        st.markdown(
            f"""
            <div class="linkedin-mockup">
                <div class="linkedin-header">
                    <div class="avatar-circle">DS</div>
                    <div>
                        <p class="author-name">
                            <span>You</span>
                            <span style="font-size:0.75rem; color:#64748b; font-weight:500;">• 1st</span>
                        </p>
                        <p class="author-title">{user_persona}</p>
                        <div class="author-time">
                            <span>Just now</span> • <span>🌐 Public</span>
                        </div>
                    </div>
                </div>
                <div class="post-content-preview">{clean_display_text}</div>
                <div class="linkedin-reactions-bar">
                    <div style="display:flex; align-items:center;">
                        <span class="reaction-icons">👍💡👏</span>
                        <span style="font-weight:600; color:#475569;">148</span>
                    </div>
                    <div>
                        <span>32 comments</span> • <span>14 reposts</span>
                    </div>
                </div>
                <div class="linkedin-footer">
                    <span>👍 Like</span>
                    <span>💬 Comment</span>
                    <span>🔄 Repost</span>
                    <span>🚀 Send</span>
                </div>
            </div>
            """,
            unsafe_allow_html=True,
        )


# ==========================================
# TAB 4: SAVED DRAFTS & HISTORY ARCHIVES
# ==========================================
with tab_history:
    st.subheader("Saved Drafts & Post Archives")
    st.caption("Locally saved in SQLite database. Search, edit, star, publish, or export.")

    col_h_search, col_h_fav, col_h_exp = st.columns([3, 2, 2])
    with col_h_search:
        draft_search = st.text_input("Search archives...", placeholder="Search drafts by keyword or tag", label_visibility="collapsed")
    with col_h_fav:
        filter_favorites = st.checkbox("⭐ Starred Only", value=False)
    with col_h_exp:
        export_mode = st.selectbox("Export Format", ["Markdown (.md)", "JSON (.json)"], label_visibility="collapsed")

    # Fetch stored drafts
    stored_drafts = get_all_drafts(favorites_only=filter_favorites, search_query=draft_search)

    # Export buttons
    col_exp_btn, _ = st.columns([2, 5])
    with col_exp_btn:
        if export_mode == "JSON (.json)":
            json_data = export_drafts_json()
            st.download_button(
                "📥 Download All as JSON",
                data=json_data,
                file_name="linkedin_ghostwriter_drafts.json",
                mime="application/json",
                use_container_width=True,
            )
        else:
            md_data = export_drafts_markdown()
            st.download_button(
                "📄 Download All as Markdown",
                data=md_data,
                file_name="linkedin_ghostwriter_drafts.md",
                mime="text/markdown",
                use_container_width=True,
            )

    st.markdown("<hr style='margin: 16px 0;'>", unsafe_allow_html=True)

    if not stored_drafts:
        st.info("No saved drafts found matching your criteria.")
    else:
        active_token = linkedin_token_input or session_linkedin_token
        for d in stored_drafts:

            d_id = d["id"]
            is_fav = d.get("is_favorite") == 1
            star_label = "⭐" if is_fav else "☆"

            with st.expander(f"{star_label} [{d.get('tone', 'Post')}] {d['title']} ({d['created_at'][:10]})", expanded=False):
                st.markdown(f"**Tone:** `{d.get('tone')}` | **Source:** `{d.get('source_type')}` | **Created:** `{d.get('created_at')}`")
                if d.get("source_url"):
                    st.markdown(f"**Source Link:** [{d['source_url']}]({d['source_url']})")
                
                draft_body = st.text_area(f"Content (Draft #{d_id})", value=d["full_content"], height=200, key=f"draft_txt_{d_id}")

                c_act1, c_act2, c_act3, c_act4, c_act5 = st.columns([2, 1.5, 1.2, 1.2, 1])
                
                with c_act1:
                    # 1-Click Publish directly from Tab 4 Drafts
                    if st.button(f"🚀 Publish to LinkedIn", key=f"pub_draft_{d_id}", type="primary", use_container_width=True):
                        if not active_token:
                            st.warning("Please connect your LinkedIn account in the sidebar first!")
                        else:
                            with st.spinner("Publishing draft to LinkedIn..."):
                                pub_res = publish_post_to_linkedin(
                                    access_token=active_token,
                                    text_content=draft_body,
                                    author_urn=linkedin_urn_input if linkedin_urn_input else None,
                                    article_url=d.get("source_url"),
                                )
                                if pub_res["success"]:
                                    st.balloons()
                                    post_url = pub_res.get("post_url", "https://www.linkedin.com/feed/")
                                    st.success(f"🎉 Draft #{d_id} published to LinkedIn!")
                                    st.markdown(f"👉 **[View live post on LinkedIn ↗]({post_url})**")
                                else:
                                    st.error(pub_res["error"])

                with c_act2:
                    if st.button("📋 Load into Studio", key=f"load_{d_id}", use_container_width=True):
                        set_editor_content(draft_body)
                        st.session_state.selected_story = {
                            "title": d["title"],
                            "content": draft_body,
                            "url": d.get("source_url", ""),
                            "source": d.get("source_type", "Draft"),
                        }
                        st.success(f"Draft #{d_id} loaded into Studio! Switch to Tab 3.")
                with c_act3:
                    fav_btn_text = "Unstar" if is_fav else "⭐ Star"
                    if st.button(fav_btn_text, key=f"fav_{d_id}", use_container_width=True):
                        toggle_favorite(d_id)
                        st.rerun()
                with c_act4:
                    if st.button("Update Text", key=f"update_{d_id}", use_container_width=True):
                        update_draft(d_id, title=d["title"], full_content=draft_body)
                        st.success("Draft updated!")
                with c_act5:
                    if st.button("🗑️ Delete", key=f"del_{d_id}", use_container_width=True):
                        delete_draft(d_id)
                        st.warning(f"Draft #{d_id} deleted.")
                        st.rerun()

