#!/usr/bin/env python3

# INSTALL: pip install google-api-python-client google-auth-oauthlib
# USAGE: ./playlistItems_delete.py $id1 [$id2 ...]

import os, sys

import google_auth_oauthlib.flow
from google.oauth2.credentials import Credentials
import googleapiclient.discovery
import googleapiclient.errors


YOUR_CLIENT_SECRET_FILE = "client_secret_CLIENTID.json"
TOKEN_FILENAME = "token.json"
SCOPES = ["https://www.googleapis.com/auth/youtube.force-ssl"]


def playlistItems_delete(items_ids):
    if os.path.exists(TOKEN_FILENAME):
        credentials = Credentials.from_authorized_user_file(TOKEN_FILENAME, SCOPES)
    else:
        # Get credentials and create an API client
        flow = google_auth_oauthlib.flow.InstalledAppFlow.from_client_secrets_file(
            YOUR_CLIENT_SECRET_FILE, scopes=SCOPES)
        credentials = flow.run_local_server(port=0)
        with open(TOKEN_FILENAME, "w", encoding="utf8") as credentials_file:
            credentials_file.write(credentials.to_json())
    youtube = googleapiclient.discovery.build("youtube", "v3", credentials=credentials)

    for item_id in items_ids:
        youtube.playlistItems().delete(id=item_id).execute()
        print(f"Playlist item successfully deleted: {item_id}")


if __name__ == '__main__':
    playlistItems_delete(sys.argv[1:])
