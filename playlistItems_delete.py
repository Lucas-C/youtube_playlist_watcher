#!/usr/bin/env python3

# INSTALL: pip install google-api-python-client google-auth-oauthlib
# USAGE: ./playlistItems_delete.py $id1 [$id2 ...]

import sys

import google_auth_oauthlib.flow
import googleapiclient.discovery
import googleapiclient.errors


YOUR_CLIENT_SECRET_FILE = "client_secret_CLIENTID.json"


def playlistItems_delete(items_ids):
    # Disable OAuthlib's HTTPS verification when running locally.
    # os.environ["OAUTHLIB_INSECURE_TRANSPORT"] = "1"

    # Get credentials and create an API client
    flow = google_auth_oauthlib.flow.InstalledAppFlow.from_client_secrets_file(
        YOUR_CLIENT_SECRET_FILE, scopes=["https://www.googleapis.com/auth/youtube.force-ssl"])
    credentials = flow.run_console()
    youtube = googleapiclient.discovery.build("youtube", "v3", credentials=credentials)

    for item_id in items_ids:
        youtube.playlistItems().delete(id=item_id).execute()


if __name__ == '__main__':
    playlistItems_delete(sys.argv[1:])
