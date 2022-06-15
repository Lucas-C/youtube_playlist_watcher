#!/usr/bin/env python3

# Does not work because this endpoint also requires an OAuth2 access token

# USAGE: YOUTUBE_API_KEY=... ./playlistItems_delete.py $id1 [$id2 ...]

import os, requests, sys


def playlistItems_delete(youtube_api_key, items_ids):
    for item_id in items_ids:
        resp = requests.delete('https://www.googleapis.com/youtube/v3/playlistItems', params={
            'key': youtube_api_key,
            'id': item_id,
        })
        if resp != 200:
            print(resp.text, file=sys.stderr)
        resp.raise_for_status()


if __name__ == '__main__':
    playlistItems_delete(os.environ['YOUTUBE_API_KEY'], sys.argv[1:])
