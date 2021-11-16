#!/usr/bin/env python3

# USAGE: ./get_youtube_video_topics.py $API_KEY $VIDEO_ID

import sys
from youtube_playlist_watcher import list_videos_details_paginated


def get_videos_topics(youtube_api_key, video_ids):
    video_topics_per_id = {}
    for response in list_videos_details_paginated(youtube_api_key, video_ids, part='topicDetails'):
        for item in response['items']:
            video_topics_per_id[item['id']] = [cat.replace('https://en.wikipedia.org/wiki/', '') for cat in item['topicDetails']['topicCategories']]
    return video_topics_per_id


if __name__ == '__main__':
    api_key, vid = sys.argv[1], sys.argv[2]
    video_topics = get_videos_topics(api_key, [vid])
    print(video_topics[vid])
