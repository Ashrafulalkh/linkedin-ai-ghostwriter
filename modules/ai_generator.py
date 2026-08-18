"""
AI Generation Engine powered by Google Gen AI SDK (`google-genai`) and OpenAI (`openai`).
"""

import json
import os
from typing import Any, Dict, List, Optional
from dotenv import load_dotenv
from google import genai
from google.genai import types
from google.genai.errors import APIError
from pydantic import BaseModel, Field

load_dotenv()

TONE_PROFILES: Dict[str, Dict[str, str]] = {
    "Pragmatic Engineer": {
        "description": "Ground-level engineering reality, production trade-offs, architecture decisions, and anti-hype practicality.",
        "voice": "Direct, experienced, analytical, empathetic to developers maintaining production systems.",
    },
    "Deep Technical Breakdown": {
        "description": "Deconstructing algorithms, system benchmarks, low-level mechanics, and data pipelines.",
        "voice": "Authoritative, educational, precise, using clean visual lists and concrete technical terminology.",
    },
    "Building in Public / Founder": {
        "description": "Sharing raw lessons, metric milestones, architectural pivots, and real-world experiments.",
        "voice": "Transparent, energetic, humble yet ambitious, relatable to builders and tech entrepreneurs.",
    },
    "Contrarian Tech Insight": {
        "description": "Challenging mainstream buzzwords, dissecting premature optimizations, and debunking hype.",
        "voice": "Thought-provoking, well-reasoned, skeptical, backed by engineering first-principles.",
    },
    "AI / Data Science Practitioner": {
        "description": "Fine-tuning insights, RAG pipelines, evaluations, embeddings, latency/cost trade-offs.",
        "voice": "Empirical, benchmark-driven, code-aware, focused on real-world AI deployment ROI.",
    },
}

SUPPORTED_PROVIDERS = [
    "Google Gemini",
    "OpenAI (ChatGPT)",
]

SUPPORTED_GEMINI_MODELS = [
    "gemini-3.7-flash",
    "gemini-3.6-flash",
    "gemini-3.5-flash",
    "gemini-flash-latest",
    "gemini-3.1-flash-lite",
    "gemini-pro-latest",
]

SUPPORTED_OPENAI_MODELS = [
    "gpt-4o",
    "gpt-4o-mini",
    "o3-mini",
    "gpt-4-turbo",
    "gpt-3.5-turbo",
]

# Default alias for backward compatibility
SUPPORTED_MODELS = SUPPORTED_GEMINI_MODELS


class LinkedInPostStructure(BaseModel):
    """Pydantic Schema for Structured LinkedIn Post Generation."""
    hook_option_1: str = Field(
        description="First high-impact, scroll-stopping hook option (curiosity or contrarian angle)."
    )
    hook_option_2: str = Field(
        description="Second high-impact, scroll-stopping hook option (data-backed or story/lesson angle)."
    )
    selected_hook: str = Field(
        description="The strongest recommended hook to open the post."
    )
    body: str = Field(
        description="2-3 short, scannable paragraphs or bullet points with ample white space."
    )
    technical_takeaway: str = Field(
        description="1-2 sentences of actionable, high-value engineering or data science advice."
    )
    discussion_question: str = Field(
        description="An open-ended question designed to spark thoughtful discussions in the comments."
    )
    hashtags: List[str] = Field(
        description="List of 3 to 4 specific, relevant hashtags (e.g. #MachineLearning, #Python, #SystemDesign)."
    )
    full_assembled_post: str = Field(
        description="The complete, publication-ready LinkedIn post combining hook, body, takeaway, question, and hashtags."
    )


def get_genai_client(api_key: Optional[str] = None) -> genai.Client:
    """Initialize and return a google-genai Client with support for AI Studio and Vertex AI."""
    key = api_key or os.getenv("GEMINI_API_KEY")
    use_vertex = os.getenv("GOOGLE_GENAI_USE_VERTEXAI", "false").lower() in ("true", "1", "yes")
    project = os.getenv("GOOGLE_CLOUD_PROJECT") or os.getenv("GCP_PROJECT_ID")
    location = os.getenv("GOOGLE_CLOUD_LOCATION", "us-central1")

    if use_vertex or project:
        return genai.Client(
            vertexai=True,
            project=project,
            location=location,
            api_key=key.strip() if key else None,
        )

    if not key or not key.strip():
        raise ValueError(
            "Gemini API Key is missing. Please provide it in the sidebar or set GEMINI_API_KEY in your .env file."
        )
    return genai.Client(api_key=key.strip())


def get_openai_client(api_key: Optional[str] = None) -> Any:
    """Initialize and return an OpenAI Client."""
    key = api_key or os.getenv("OPENAI_API_KEY")
    if not key or not key.strip():
        raise ValueError(
            "OpenAI API Key is missing. Please enter it in the sidebar or set OPENAI_API_KEY in your .env file."
        )
    try:
        from openai import OpenAI
    except ImportError:
        raise ImportError(
            "The 'openai' Python package is not installed. Please run: pip install openai"
        )
    
    base_url = os.getenv("OPENAI_BASE_URL")
    if base_url:
        return OpenAI(api_key=key.strip(), base_url=base_url)
    return OpenAI(api_key=key.strip())


def build_system_prompt(persona: str, tone_name: str) -> str:
    """Construct an expert ghostwriting system instruction."""
    tone_info = TONE_PROFILES.get(tone_name, TONE_PROFILES["Pragmatic Engineer"])
    
    return f"""You are an elite LinkedIn Ghostwriter and Principal Engineer / Staff Data Scientist.
Your goal is to write high-engagement, high-signal LinkedIn posts that establish authority, educate tech peers, and spark meaningful engineering discussions.

Target Persona: {persona}
Writing Tone: {tone_name} ({tone_info['description']})
Voice Guidelines: {tone_info['voice']}

Key LinkedIn Best Practices:
1. THE HOOK: The first 2 lines determine if readers click '...see more'. Make it punchy, intriguing, contrarian, or insight-packed. Avoid cheesy clickbait, emojis spam, or '🚀 Excited to share!'.
2. READABILITY: Use short 1-2 sentence paragraphs. Leave empty lines for whitespace. Use clean bullet points (• or ↳) where appropriate.
3. SUBSTANCE OVER FLUFF: Give concrete technical insights, architectural trade-offs, or real-world practicalities.
4. CALL TO ACTION / QUESTION: End with a genuine, specific question that engineers and data scientists want to answer.
5. HASHTAGS: Exactly 3 to 4 niche, relevant tags at the bottom.
6. NO CORPORATE JARGON: Ban words like 'synergy', 'game changer', 'paradigm shift', 'delighted to announce'.
"""


def _generate_with_openai(
    topic_title: str,
    topic_content: str,
    tone: str,
    persona: str,
    custom_notes: Optional[str],
    target_length: str,
    model_name: str,
    api_key: Optional[str],
    temperature: float,
) -> Dict[str, Any]:
    """Generate structured LinkedIn post using OpenAI API."""
    try:
        client = get_openai_client(api_key)
        system_prompt = build_system_prompt(persona, tone)

        user_prompt = f"""Craft a high-signal LinkedIn post based on the following tech topic / research / article.

Topic Title: {topic_title}

Context / Article Content:
{topic_content if topic_content else 'Focus on the topic title and core engineering implications.'}

Target Length Preference: {target_length}
Additional Custom Instructions / Angles from the User: {custom_notes or 'None - focus on top engineering takeaways.'}

Please return the response adhering strictly to the JSON schema with two distinct hook options, scannable body, technical takeaway, discussion question, 3-4 hashtags, and the complete assembled post.
"""
        kwargs = {}
        # Avoid passing temperature to reasoning models like o1 or o3-mini which only accept default
        if not (model_name.startswith("o1") or model_name.startswith("o3")):
            kwargs["temperature"] = temperature

        completion = client.beta.chat.completions.parse(
            model=model_name,
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt},
            ],
            response_format=LinkedInPostStructure,
            **kwargs,
        )

        message = completion.choices[0].message
        if message.parsed:
            parsed_data = message.parsed.model_dump()
        else:
            parsed_data = json.loads(message.content or "{}")

        return {
            "success": True,
            "data": parsed_data,
            "error": None,
            "model_used": model_name,
            "provider_used": "OpenAI (ChatGPT)",
        }
    except Exception as e:
        return {
            "success": False,
            "data": None,
            "error": f"OpenAI Error ({model_name}): {str(e)}",
            "model_used": model_name,
            "provider_used": "OpenAI (ChatGPT)",
        }


def _generate_with_gemini(
    topic_title: str,
    topic_content: str,
    tone: str,
    persona: str,
    custom_notes: Optional[str],
    target_length: str,
    model_name: str,
    api_key: Optional[str],
    temperature: float,
) -> Dict[str, Any]:
    """Generate structured LinkedIn post using Google Gen AI SDK."""
    client = get_genai_client(api_key)
    system_prompt = build_system_prompt(persona, tone)

    user_prompt = f"""Craft a high-signal LinkedIn post based on the following tech topic / research / article.

Topic Title: {topic_title}

Context / Article Content:
{topic_content if topic_content else 'Focus on the topic title and core engineering implications.'}

Target Length Preference: {target_length}
Additional Custom Instructions / Angles from the User: {custom_notes or 'None - focus on top engineering takeaways.'}

Please return the response adhering strictly to the JSON schema with two distinct hook options, scannable body, technical takeaway, discussion question, 3-4 hashtags, and the complete assembled post.
"""

    fallback_models = [model_name]
    if model_name != "gemini-3.6-flash":
        fallback_models.append("gemini-3.6-flash")
    if "gemini-flash-latest" not in fallback_models:
        fallback_models.append("gemini-flash-latest")

    last_error = ""
    for candidate_model in fallback_models:
        try:
            response = client.models.generate_content(
                model=candidate_model,
                contents=user_prompt,
                config=types.GenerateContentConfig(
                    response_mime_type="application/json",
                    response_schema=LinkedInPostStructure,
                    temperature=temperature,
                    system_instruction=system_prompt,
                ),
            )

            raw_text = response.text
            if not raw_text:
                raise ValueError("Empty response received from Gemini model.")

            parsed_data = json.loads(raw_text)
            return {
                "success": True,
                "data": parsed_data,
                "error": None,
                "model_used": candidate_model,
                "provider_used": "Google Gemini",
            }
        except APIError as e:
            msg = e.message or str(e)
            if "User location is not supported" in msg or "location" in msg.lower():
                last_error = (
                    f"Google Gemini API Error ({candidate_model}): {msg}. "
                    "Google restricts Gemini API calls from certain geographical IP locations. "
                    "Tip: Connect via a VPN set to a supported region (such as USA, UK, Germany, or Singapore), "
                    "set an HTTPS_PROXY, or switch to OpenAI (ChatGPT) in the sidebar!"
                )
            else:
                last_error = f"Google Gemini API Error ({candidate_model}): {msg}"
            continue
        except Exception as e:
            msg = str(e)
            if "User location is not supported" in msg:
                last_error = (
                    f"Generation Error ({candidate_model}): {msg}. "
                    "Tip: Connect via a VPN or switch to OpenAI (ChatGPT) in the sidebar."
                )
            else:
                last_error = f"Generation Error ({candidate_model}): {msg}"
            continue

    return {
        "success": False,
        "data": None,
        "error": last_error,
        "model_used": model_name,
        "provider_used": "Google Gemini",
    }


def generate_linkedin_post(
    topic_title: str,
    topic_content: str,
    tone: str = "Pragmatic Engineer",
    persona: str = "Software & Data Science Professional",
    custom_notes: Optional[str] = None,
    target_length: str = "Medium (150-250 words)",
    model_name: str = "gemini-3.7-flash",
    api_key: Optional[str] = None,
    temperature: float = 0.7,
    provider: str = "Google Gemini",
) -> Dict[str, Any]:
    """Generate a structured LinkedIn post using either Google Gemini or OpenAI ChatGPT."""
    is_openai = provider == "OpenAI (ChatGPT)" or model_name.startswith(("gpt-", "o1-", "o3-", "chatgpt"))
    
    if is_openai:
        return _generate_with_openai(
            topic_title=topic_title,
            topic_content=topic_content,
            tone=tone,
            persona=persona,
            custom_notes=custom_notes,
            target_length=target_length,
            model_name=model_name if not model_name.startswith("gemini") else "gpt-4o-mini",
            api_key=api_key,
            temperature=temperature,
        )
    else:
        return _generate_with_gemini(
            topic_title=topic_title,
            topic_content=topic_content,
            tone=tone,
            persona=persona,
            custom_notes=custom_notes,
            target_length=target_length,
            model_name=model_name,
            api_key=api_key,
            temperature=temperature,
        )


def regenerate_hooks(
    post_body: str,
    tone: str = "Pragmatic Engineer",
    api_key: Optional[str] = None,
    model_name: str = "gemini-2.5-flash",
    provider: str = "Google Gemini",
) -> List[str]:
    """Generate 3 fresh scroll-stopping hooks for an existing post."""
    prompt = f"""Given this LinkedIn post body:
\"\"\"{post_body}\"\"\"

Generate 3 brand-new, ultra-compelling LinkedIn hook opening lines (1-2 sentences each) in a '{tone}' tone.
Return ONLY a raw JSON array of 3 strings, e.g. ["Hook 1...", "Hook 2...", "Hook 3..."]."""

    is_openai = provider == "OpenAI (ChatGPT)" or model_name.startswith(("gpt-", "o1-", "o3-", "chatgpt"))

    if is_openai:
        try:
            client = get_openai_client(api_key)
            eff_model = model_name if model_name.startswith(("gpt-", "o1-", "o3-")) else "gpt-4o-mini"
            kwargs = {}
            if not (eff_model.startswith("o1") or eff_model.startswith("o3")):
                kwargs["temperature"] = 0.8
            response = client.chat.completions.create(
                model=eff_model,
                messages=[{"role": "user", "content": prompt}],
                **kwargs,
            )
            raw = response.choices[0].message.content or "[]"
            # Clean markdown codeblocks if model returned ```json ... ```
            cleaned = raw.strip()
            if cleaned.startswith("```"):
                lines = cleaned.split("\n")
                if lines[0].startswith("```"):
                    lines = lines[1:]
                if lines and lines[-1].startswith("```"):
                    lines = lines[:-1]
                cleaned = "\n".join(lines).strip()
            parsed = json.loads(cleaned)
            if isinstance(parsed, list):
                return parsed
            if isinstance(parsed, dict):
                for v in parsed.values():
                    if isinstance(v, list):
                        return v
            return []
        except Exception:
            return []

    try:
        client = get_genai_client(api_key)
        response = client.models.generate_content(
            model=model_name,
            contents=prompt,
            config=types.GenerateContentConfig(
                response_mime_type="application/json",
                temperature=0.8,
            ),
        )
        hooks = json.loads(response.text)
        return hooks if isinstance(hooks, list) else []
    except Exception:
        return []

