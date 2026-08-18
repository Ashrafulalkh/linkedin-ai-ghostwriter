"""
1-Click LinkedIn OAuth 2.0 Helper Script.
Run this script to authenticate your LinkedIn account and automatically save the access token to your .env file.
"""

import http.server
import os
import socketserver
import urllib.parse
import webbrowser
import requests
from dotenv import load_dotenv

load_dotenv()

PORT = 8505
REDIRECT_URI = f"http://localhost:{PORT}/callback"

CLIENT_ID = os.getenv("LINKEDIN_CLIENT_ID", "")
CLIENT_SECRET = os.getenv("LINKEDIN_CLIENT_SECRET", "")


class OAuthHandler(http.server.SimpleHTTPRequestHandler):
    def do_GET(self):
        parsed = urllib.parse.urlparse(self.path)
        if parsed.path == "/callback":
            query_params = urllib.parse.parse_qs(parsed.query)
            if "code" in query_params:
                code = query_params["code"][0]
                self.send_response(200)
                self.send_header("Content-type", "text/html")
                self.end_headers()
                self.wfile.write(b"""
                    <html><body style="font-family:sans-serif; text-align:center; padding:50px;">
                        <h2 style="color:#0A66C2;">&#10004; LinkedIn Authorization Successful!</h2>
                        <p>You can close this tab and return to your terminal / Streamlit app.</p>
                    </body></html>
                """)
                self.server.auth_code = code
            else:
                self.send_response(400)
                self.end_headers()
                self.wfile.write(b"Failed: No authorization code received.")
        else:
            self.send_response(404)
            self.end_headers()


def authenticate():
    global CLIENT_ID, CLIENT_SECRET
    print("\n" + "=" * 60)
    print("⚡ LinkedIn 1-Click OAuth Setup Helper")
    print("=" * 60)

    if not CLIENT_ID:
        CLIENT_ID = input("\nEnter your LinkedIn App Client ID: ").strip()
    if not CLIENT_SECRET:
        CLIENT_SECRET = input("Enter your LinkedIn App Client Secret: ").strip()

    if not CLIENT_ID or not CLIENT_SECRET:
        print("❌ Error: Client ID and Client Secret are required.")
        return

    # Build Auth URL
    auth_params = {
        "response_type": "code",
        "client_id": CLIENT_ID,
        "redirect_uri": REDIRECT_URI,
        "scope": "w_member_social openid profile email",
        "state": "ghostwriter_auth_state",
    }
    auth_url = f"https://www.linkedin.com/oauth/v2/authorization?{urllib.parse.urlencode(auth_params)}"

    print(f"\n1. Make sure '{REDIRECT_URI}' is added to Authorized Redirect URLs in your LinkedIn App Auth tab.")
    print(f"2. Opening LinkedIn Login in your browser...\n")
    webbrowser.open(auth_url)

    # Listen on local server for the callback
    with socketserver.TCPServer(("", PORT), OAuthHandler) as httpd:
        httpd.auth_code = None
        print(f"Waiting for authorization callback at {REDIRECT_URI} ...")
        while not httpd.auth_code:
            httpd.handle_request()
        auth_code = httpd.auth_code

    print(f"\n✔ Authorization code received! Exchanging for Access Token...")

    # Exchange authorization code for access token
    token_url = "https://www.linkedin.com/oauth/v2/accessToken"
    token_data = {
        "grant_type": "authorization_code",
        "code": auth_code,
        "redirect_uri": REDIRECT_URI,
        "client_id": CLIENT_ID,
        "client_secret": CLIENT_SECRET,
    }

    resp = requests.post(token_url, data=token_data)
    if resp.status_code == 200:
        token_json = resp.json()
        access_token = token_json.get("access_token")
        print("\n" + "=" * 60)
        print("🎉 SUCCESS! LinkedIn Access Token Generated:")
        print(f"Token: {access_token[:20]}...{access_token[-10:]}")
        print("=" * 60)

        # Update .env file
        env_path = os.path.join(os.path.dirname(__file__), ".env")
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
            elif line.startswith("LINKEDIN_CLIENT_ID="):
                new_lines.append(f"LINKEDIN_CLIENT_ID={CLIENT_ID}\n")
            elif line.startswith("LINKEDIN_CLIENT_SECRET="):
                new_lines.append(f"LINKEDIN_CLIENT_SECRET={CLIENT_SECRET}\n")
            else:
                new_lines.append(line)

        if not updated:
            new_lines.append(f"LINKEDIN_ACCESS_TOKEN={access_token}\n")
            new_lines.append(f"LINKEDIN_CLIENT_ID={CLIENT_ID}\n")
            new_lines.append(f"LINKEDIN_CLIENT_SECRET={CLIENT_SECRET}\n")

        with open(env_path, "w") as f:
            f.writelines(new_lines)

        print("\n✔ Saved LINKEDIN_ACCESS_TOKEN automatically to your .env file!")
        print("You can now refresh Streamlit and publish directly to LinkedIn!\n")
    else:
        print(f"❌ Failed to exchange token (HTTP {resp.status_code}): {resp.text}")


if __name__ == "__main__":
    authenticate()
