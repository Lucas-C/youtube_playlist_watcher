#!/usr/bin/env python3

# Utility script to extract videos durations from JSON dump files,
# so that it can be piped to jq, for example, for sorting:

# USAGE: ./songs_by_duration.py youtube-playlist-$playlistId-$timestamp.json | jq 'sort_by(.duration)' | tail -n 50

import json, sys

with open(sys.argv[1], encoding='utf-8') as json_file:
    playlist = json.load(json_file)

def parse_ptime(duration):  # e.g. PT1H32H15
    duration = duration[2:]
    out = [0, 0 ,0]
    if 'H' in duration:
        out[0], duration = duration.split('H')
    if 'M' in duration:
        out[1], duration = duration.split('M')
    if 'S' in duration:
        out[2], _ = duration.split('S')
    return tuple(map(int, out))

def transform(song):
    return {
        'title': song['snippet']['title'],
        'url': 'https://www.youtube.com/watch?v=' + song['id'],
        'duration': parse_ptime(song['contentDetails']['duration']),
    }

print(json.dumps(sorted(map(transform, playlist), key=lambda song: song['duration']), indent=4))
