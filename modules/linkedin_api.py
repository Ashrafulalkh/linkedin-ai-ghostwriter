"""
LinkedIn API Integration Module for direct posting (REST API) and Web Composer Intents.
"""

import os
import urllib.parse
from typing import Any, Dict, Optional
import requests


def generate_web_composer_url(text: str, url: Optional[str] = None) -> str:
    """
    Generate an instant LinkedIn web intent URL to open LinkedIn composer pre-filled.
    """
    base_url = "https://www.linkedin.com/feed/"
    # If an article link is provided, share-offsite opens the preview dialog
    if url and url.startswith("http"):
        encoded_url = urllib.parse.quote(url, safe="")
        return f"https://www.linkedin.com/sharing/share-offsite/?url={encoded_url}"
    return base_url


def get_linkedin_user_profile(access_token: str, timeout: int = 8) -> Dict[str, Any]:
    """
    Fetch connected LinkedIn profile information using OpenID Connect (/v2/userinfo) or /v2/me.
    """
    if not access_token or not access_token.strip():
        return {"success": False, "error": "Access token is empty."}

    token = access_token.strip()
    headers = {
        "Authorization": f"Bearer {token}",
        "Content-Type": "application/json",
    }

    # 1. Try standard OpenID Connect /v2/userinfo endpoint (Modern LinkedIn OAuth)
    try:
        resp = requests.get("https://api.linkedin.com/v2/userinfo", headers=headers, timeout=timeout)
        if resp.status_code == 200:
            data = resp.json()
            sub_id = data.get("sub")
            name = data.get("name") or f"{data.get('given_name', '')} {data.get('family_name', '')}".strip()
            picture = data.get("picture", "")
            urn = f"urn:li:person:{sub_id}" if sub_id and not str(sub_id).startswith("urn:li:") else str(sub_id or "")
            return {
                "success": True,
                "urn": urn,
                "name": name or "LinkedIn User",
                "picture": picture,
                "email": data.get("email", ""),
            }
        elif resp.status_code == 403:
            return {
                "success": False,
                "error": (
                    "403 Forbidden: Your token only has 'w_member_social' (Write permission). "
                    "To enable auto profile detection, go to your LinkedIn App -> Products tab -> "
                    "request 'Sign In with LinkedIn using OpenID Connect', then regenerate your token with 'openid' and 'profile' selected. "
                    "Alternatively, you can manually enter your LinkedIn Member URN in the sidebar."
                ),
            }
    except Exception:
        pass

    # 2. Fallback to /v2/me legacy endpoint
    try:
        resp_me = requests.get("https://api.linkedin.com/v2/me", headers=headers, timeout=timeout)
        if resp_me.status_code == 200:
            data = resp_me.json()
            user_id = data.get("id")
            first_name = data.get("localizedFirstName", "")
            last_name = data.get("localizedLastName", "")
            urn = f"urn:li:person:{user_id}" if user_id and not str(user_id).startswith("urn:li:") else str(user_id or "")
            return {
                "success": True,
                "urn": urn,
                "name": f"{first_name} {last_name}".strip() or "LinkedIn User",
                "picture": "",
            }
        else:
            return {
                "success": False,
                "error": (
                    f"LinkedIn Profile Read Error (HTTP {resp_me.status_code}): "
                    "Your token lacks profile read permissions ('openid' / 'profile'). "
                    "Please add 'Sign In with LinkedIn using OpenID Connect' in Products tab, or specify your Person URN manually in the sidebar."
                ),
            }
    except Exception as e:
        return {
            "success": False,
            "error": f"Failed to connect to LinkedIn API: {str(e)}",
        }


def _decode_jwt_payload_safe(token_str: str) -> Dict[str, Any]:
    """Safely decode payload of an unverified JWT (e.g. OpenID id_token)."""
    import base64
    import json
    try:
        parts = token_str.split(".")
        if len(parts) >= 2:
            payload_b64 = parts[1] + "=" * (-len(parts[1]) % 4)
            payload_bytes = base64.urlsafe_b64decode(payload_b64.encode("utf-8"))
            return json.loads(payload_bytes.decode("utf-8"))
    except Exception:
        pass
    return {}


def exchange_authorization_code(
    code: str,
    client_id: str,
    client_secret: str,
    redirect_uri: str = "http://localhost:8501",
    timeout: int = 10,
) -> Dict[str, Any]:
    """
    Exchange OAuth 2.0 authorization code for a LinkedIn Access Token.
    Extracts OpenID id_token payload if available.
    """
    token_url = "https://www.linkedin.com/oauth/v2/accessToken"
    payload = {
        "grant_type": "authorization_code",
        "code": code.strip(),
        "redirect_uri": redirect_uri,
        "client_id": client_id.strip(),
        "client_secret": client_secret.strip(),
    }

    try:
        resp = requests.post(token_url, data=payload, timeout=timeout)
        if resp.status_code == 200:
            data = resp.json()
            access_token = data.get("access_token")
            id_token = data.get("id_token")
            
            author_urn = None
            user_name = None
            if id_token:
                jwt_payload = _decode_jwt_payload_safe(id_token)
                sub_val = jwt_payload.get("sub")
                if sub_val:
                    author_urn = f"urn:li:person:{sub_val}" if not str(sub_val).startswith("urn:li:") else str(sub_val)
                user_name = jwt_payload.get("name") or jwt_payload.get("given_name")

            return {
                "success": True,
                "access_token": access_token,
                "expires_in": data.get("expires_in"),
                "author_urn": author_urn,
                "user_name": user_name,
                "error": None,
            }
        else:
            return {
                "success": False,
                "access_token": None,
                "error": f"OAuth exchange failed ({resp.status_code}): {resp.text}",
            }
    except Exception as e:
        return {
            "success": False,
            "access_token": None,
            "error": f"Exception during OAuth exchange: {str(e)}",
        }


def save_access_token_to_env(access_token: str) -> None:
    """Save the access token to .env file."""
    env_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), ".env")
    lines = []
    if os.path.exists(env_path):
        with open(env_path, "r") as f:
            lines = f.readlines()

    updated = False
    new_lines = []
    for line in lines:
        if line.startswith("LINKEDIN_ACCESS_TOKEN="):
            new_lines.append(f"LINKEDIN_ACCESS_TOKEN={access_token}\n")
            updated = True
        else:
            new_lines.append(line)

    if not updated:
        new_lines.append(f"LINKEDIN_ACCESS_TOKEN={access_token}\n")

    with open(env_path, "w") as f:
        f.writelines(new_lines)


def publish_post_to_linkedin(
    access_token: str,
    text_content: str,
    author_urn: Optional[str] = None,
    article_url: Optional[str] = None,
    timeout: int = 12,
) -> Dict[str, Any]:
    """
    Publish a post directly to the user's LinkedIn profile using the ugcPosts / rest posts API.
    """
    if not access_token or not access_token.strip():
        return {
            "success": False,
            "error": "LinkedIn Access Token is missing. Configure it in the sidebar or .env.",
        }

    token = access_token.strip()

    # If author URN is not provided, fetch it first
    if not author_urn:
        profile_res = get_linkedin_user_profile(token, timeout=timeout)
        if not profile_res["success"]:
            return {
                "success": False,
                "error": f"Could not determine LinkedIn author URN: {profile_res.get('error')}",
            }
        author_urn = profile_res["urn"]

    headers = {
        "Authorization": f"Bearer {token}",
        "Content-Type": "application/json",
        "X-Restli-Protocol-Version": "2.0.0",
    }

    # Construct UGC (User Generated Content) Post Payload
    media_content = {"shareMediaCategory": "NONE"}
    if article_url and (article_url.startswith("http://") or article_url.startswith("https://")):
        media_content = {
            "shareMediaCategory": "ARTICLE",
            "media": [
                {
                    "status": "READY",
                    "originalUrl": article_url,
                }
            ],
        }

    payload = {
        "author": author_urn,
        "lifecycleState": "PUBLISHED",
        "specificContent": {
            "com.linkedin.ugc.ShareContent": {
                "shareCommentary": {
                    "text": text_content,
                },
                **media_content,
            }
        },
        "visibility": {
            "com.linkedin.ugc.MemberNetworkVisibility": "PUBLIC",
        },
    }

    try:
        response = requests.post(
            "https://api.linkedin.com/v2/ugcPosts",
            json=payload,
            headers=headers,
            timeout=timeout,
        )

        if response.status_code in [200, 201]:
            resp_data = response.json()
            post_urn = resp_data.get("id", "")
            return {
                "success": True,
                "post_urn": post_urn,
                "post_url": f"https://www.linkedin.com/feed/update/{post_urn}/" if post_urn else "https://www.linkedin.com/feed/",
                "error": None,
            }
        else:
            err_text = response.text
            if "REVOKED_ACCESS_TOKEN" in err_text or "65601" in err_text:
                friendly_error = (
                    "LinkedIn Token Revoked (401): This token was revoked or expired (e.g. you re-authenticated or changed credentials). "
                    "Please reconnect LinkedIn in the sidebar, or click '🔄 Re-apply Active LinkedIn Token' on this post to retry."
                )
            elif response.status_code == 401:
                friendly_error = (
                    "LinkedIn Authentication Error (401): The access token is invalid or expired. "
                    "Please reconnect your LinkedIn account in the sidebar."
                )
            else:
                friendly_error = f"LinkedIn API Publish Error ({response.status_code}): {err_text}"

            return {
                "success": False,
                "error": friendly_error,
                "post_urn": None,
                "post_url": None,
            }
    except requests.exceptions.Timeout:
        return {
            "success": False,
            "error": "Request timed out while sending post to LinkedIn.",
            "post_urn": None,
            "post_url": None,
        }
    except Exception as e:
        return {
            "success": False,
            "error": f"Publishing exception: {str(e)}",
            "post_urn": None,
            "post_url": None,
        }
