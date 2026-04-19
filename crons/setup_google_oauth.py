"""
setup_google_oauth.py — One-time OAuth setup for Google Sheets access.

Run this ONCE on your local machine (needs browser) to:
1. Open browser for Google login (use academie@academiexguard.ca)
2. Get a refresh token
3. Save token to secrets/google_token.json

After this, the cron can access the sheet forever without re-auth
(unless the token is revoked).

PREREQUISITE: Download OAuth 2.0 Client ID credentials from GCP console
and save to: secrets/google_oauth.json

Steps to get google_oauth.json:
1. Go to https://console.cloud.google.com/
2. Select or create a project (or reuse "mattermost-securite")
3. APIs & Services -> Library -> Enable "Google Sheets API"
4. APIs & Services -> Credentials -> Create Credentials -> OAuth client ID
5. Application type: Desktop app
6. Name: "XGuard Sheets Sync"
7. Download JSON -> save as secrets/google_oauth.json
"""

import os
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))

from google_auth_oauthlib.flow import InstalledAppFlow
from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials

from kb_config import GOOGLE_OAUTH_JSON, GOOGLE_TOKEN_JSON, GOOGLE_SHEETS_SCOPES


def main():
    creds = None

    # Check if token already exists
    if os.path.exists(GOOGLE_TOKEN_JSON):
        print(f"Existing token found: {GOOGLE_TOKEN_JSON}")
        try:
            creds = Credentials.from_authorized_user_file(GOOGLE_TOKEN_JSON, GOOGLE_SHEETS_SCOPES)
            if creds and creds.valid:
                print("Token is valid, no re-auth needed")
                return
            if creds and creds.expired and creds.refresh_token:
                print("Token expired, refreshing...")
                creds.refresh(Request())
                with open(GOOGLE_TOKEN_JSON, "w") as token:
                    token.write(creds.to_json())
                print("Token refreshed OK")
                return
        except Exception as e:
            print(f"Token load failed: {e}")
            print("Will do fresh OAuth flow...")
            creds = None

    # Check OAuth client credentials
    if not os.path.exists(GOOGLE_OAUTH_JSON):
        print(f"ERROR: OAuth client credentials not found at {GOOGLE_OAUTH_JSON}")
        print("")
        print("Please download them from Google Cloud Console:")
        print("1. Go to https://console.cloud.google.com/apis/credentials")
        print("2. Create OAuth 2.0 Client ID (Desktop app type)")
        print("3. Download JSON")
        print(f"4. Save as: {GOOGLE_OAUTH_JSON}")
        sys.exit(1)

    # Fresh OAuth flow — opens browser
    print("Starting OAuth flow — browser will open...")
    print("IMPORTANT: Login with academie@academiexguard.ca")
    print("")

    flow = InstalledAppFlow.from_client_secrets_file(GOOGLE_OAUTH_JSON, GOOGLE_SHEETS_SCOPES)
    creds = flow.run_local_server(port=0)

    # Save the credentials for next run
    os.makedirs(os.path.dirname(GOOGLE_TOKEN_JSON), exist_ok=True)
    with open(GOOGLE_TOKEN_JSON, "w") as token:
        token.write(creds.to_json())

    print(f"Token saved to: {GOOGLE_TOKEN_JSON}")
    print("You can now run google_sheets_sync.py")


if __name__ == "__main__":
    main()
