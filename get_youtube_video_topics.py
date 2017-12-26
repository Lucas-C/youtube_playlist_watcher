#!/usr/bin/env python3

import requests, sys


VIDEOS_DETAILS_REQUEST_BATCH_SIZE = 50


def get_videos_topics(youtube_api_key, video_ids):
    video_topics_per_id = {}
    batch_start_index = 0
    while batch_start_index < len(video_ids):
        videos_ids_batch = video_ids[batch_start_index:batch_start_index + VIDEOS_DETAILS_REQUEST_BATCH_SIZE]
        response = requests.get('https://www.googleapis.com/youtube/v3/videos', params={
            'key': youtube_api_key,
            'id': ','.join(videos_ids_batch),  # it is not clearly documented, but the API does not accept more than 50 ids here
            'maxResults': VIDEOS_DETAILS_REQUEST_BATCH_SIZE,
            'part': 'topicDetails', # cf. https://developers.google.com/youtube/v3/docs/videos/list#parameters
        }).json()
        for item in response['items']:
            video_topics_per_id[item['id']] = [cat.replace('https://en.wikipedia.org/wiki/', '') for cat in item['topicDetails']['topicCategories']]
        batch_start_index += VIDEOS_DETAILS_REQUEST_BATCH_SIZE
    return video_topics_per_id


if __name__ == '__main__':
    api_key, vid = sys.argv[1], sys.argv[2]
    video_topics = get_videos_topics(api_key, [vid])
    print(video_topics[vid])
