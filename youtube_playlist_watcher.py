#!/usr/bin/env python3.4

import argparse, json, math, os, requests, string, subprocess, sys, time
from os.path import basename
from glob import glob
from tqdm import tqdm
from urllib.parse import urlencode

DUMP_FILENAME_TEMPLATE = 'youtube-playlist-{playlist_id}-{timestamp}.json'
ISO8601_TIMESTAMP_FORMAT = '%Y%m%d%H%M%S'
YOUTUBE_API_KEY = os.environ['YOUTUBE_API_KEY']
PLAYLIST_ITEMS_REQUEST_BATCH_SIZE = 50
CONTENT_DETAILS_REQUEST_BATCH_SIZE = 50
THIS_SCRIPT_PARENT_DIR = os.path.dirname(os.path.realpath(__file__))

def main(argv):
    args = parse_args(argv[1:])
    args.exec_cmd(args)

################################################################################
### CLI arguments parsing

def parse_args(argv):
    parser = argparse.ArgumentParser(description='Dump & compare the content of Youtube playlists',
                                     formatter_class=ArgparseHelpFormatter)
    parser.add_argument('--playlist-id', required=True)
    parser.add_argument('--backup-dir', default=THIS_SCRIPT_PARENT_DIR, help='folder where dumps are stored')
    subparsers = parser.add_subparsers()
    compare_parser = subparsers.add_parser('compare', formatter_class=ArgparseHelpFormatter)
    compare_parser.set_defaults(exec_cmd=compare_command)
    compare_parser.add_argument('dump1_timestamp', nargs='?', metavar='DUMP1', default='SECOND_TO_LAST',
                                help='can be just a prefix like 2015-01-01')
    compare_parser.add_argument('dump2_timestamp', nargs='?', metavar='DUMP2', default='LATEST', help='ditto')
    compare_parser.add_argument('--alert-on', type=lambda s: s.split(','),
                                choices=('ADDED', 'REMOVED', 'BECAME_PRIVATE', 'REGION_RESTRICTION_CHANGE'),
                                default=('REMOVED', 'BECAME_PRIVATE', 'REGION_RESTRICTION_CHANGE'),
                                help='Comma-separated list of changes that trigger the "alert-cmd"')
    compare_parser.add_argument('--region-watched', default='FR', help='Region watched for restrictions changes')
    compare_parser.add_argument('--alert-cmd', help='Command to run when a change is detected')
    dump_parser = subparsers.add_parser('dump', formatter_class=ArgparseHelpFormatter)
    dump_parser.set_defaults(exec_cmd=dump_command)
    purge_dumps_parser = subparsers.add_parser('purge-dumps', formatter_class=ArgparseHelpFormatter)
    purge_dumps_parser.add_argument('--keep-count', type=int, default=50, help='Number of JSON dumps to keep')
    purge_dumps_parser.set_defaults(exec_cmd=purge_dumps_command)
    return parser.parse_args(argv)

class ArgparseHelpFormatter(argparse.RawTextHelpFormatter, argparse.ArgumentDefaultsHelpFormatter):
    pass


################################################################################
### Main CLI commands

def dump_command(args):
    playlist = get_playlist_with_progressbar(args.playlist_id)
    content_details = get_content_details_with_progressbar(playlist)
    add_content_details_to_playlist(content_details, playlist)
    dump_to_file(playlist, args.playlist_id, args.backup_dir)

def purge_dumps_command(args):
    all_dumps = get_all_dumps_sorted_by_date(args.backup_dir, args.playlist_id)
    dumps_to_remove = all_dumps[args.keep_count:]
    if not dumps_to_remove:
        return
    print('Now removing the following dumps: {}'.format(' '.join([basename(f) for f in dumps_to_remove])))
    for dump in dumps_to_remove:
        os.unlink(dump)

def compare_command(args):
    print('Detecting changes in playlist https://www.youtube.com/playlist?list={} in region {}'.format(args.playlist_id, args.region_watched))
    dump1, dump2 = get_dumps(args)
    changes = get_changes(dump1, dump2, args.region_watched)
    if not any(changes.values()):
        return
    text_output = make_text_output(changes)
    print(text_output)
    alerting_changes = {type: items for (type, items) in changes.items() if type in args.alert_on and items}
    if alerting_changes and args.alert_cmd:
        print(subprocess.check_output(args.alert_cmd, input=bytes(text_output, 'UTF-8'), shell=True, stderr=subprocess.STDOUT).decode("utf-8"))


################################################################################
### Video items utility functions

def get_video_id(item):
    return item['snippet']['resourceId']['videoId']

def get_video_url(item):
    return 'https://www.youtube.com/watch?v=' + get_video_id(item)

def get_video_title(item):
    return item['snippet']['title']

def get_title_based_search_url(item):
    return 'https://www.youtube.com/results?' + urlencode({'search_query': get_video_title(item)})

def is_video_private(item):
    # Alt: retrieve the 'status' part (quota cost 2) -> item['status']['privacyStatus'] == 'private'
    if item['snippet']['description'] != 'This video is private.' and item['snippet']['title'] != 'Private video':
        return False
    if item['snippet']['description'] != 'This video is private.' or item['snippet']['title'] != 'Private video':
        raise EnvironmentError('Youtube Data API change detected')
    return True

def get_video_region_restriction(item, region_watched):
    try:
        region_restriction = item['contentDetails']['regionRestriction']
    except KeyError:
        return '{}'
    watched_region_restriction = {}
    if region_watched in region_restriction.get('allowed', []):
        watched_region_restriction['allowed'] = region_watched
    if region_watched in region_restriction.get('blocked', []):
        watched_region_restriction['blocked'] = region_watched
    return json.dumps(watched_region_restriction)


################################################################################
### Textual output generation

def make_text_output(changes):
    output_lines_iterator = (list(getattr(OutputLinesIterator, type.lower())(changeset)) for (type, changeset) in changes.items())
    return '\n'.join(sum(output_lines_iterator, []))

class OutputLinesIterator:
    @staticmethod
    def added(changeset):
        for new_item in changeset:
            yield 'ADDED: ' + get_video_title(new_item)
    @staticmethod
    def removed(changeset):
        for old_item in changeset:
            yield ('REMOVED: ' + get_video_title(old_item)
                 + ' -> find another video named like that: ' + get_title_based_search_url(old_item))
    @staticmethod
    def region_restriction_change(changeset):
        for _, (new_item, old_restricts, new_restricts) in changeset.items():
            yield ('REGION RESTRICTIONS CHANGED for ' + get_video_title(new_item) + ' : ' + old_restricts + '-> ' + new_restricts
                 + ' -> find another video named like that: ' + get_title_based_search_url(new_item))
    @staticmethod
    def became_private(changeset):
        for old_item in changeset:
            video_name = get_video_title(old_item) if not is_video_private(old_item) else get_video_url(old_item)
            yield ('BECAME PRIVATE: ' + video_name
                 + ' -> find another video named like that: ' + get_title_based_search_url(old_item))


################################################################################
### Changes detection

def get_changes(dump1, dump2, region_watched):
    changes = {}
    changes['BECAME_PRIVATE'] = [item for item in dump2 if is_video_private(item)]
    dump1_by_vid = {get_video_id(item): item for item in dump1}
    dump2_by_vid = {get_video_id(item): item for item in dump2}
    added_vids = dump2_by_vid.keys() - dump1_by_vid.keys()
    changes['ADDED'] = [dump2_by_vid[vid] for vid in added_vids]
    removed_vids = dump1_by_vid.keys() - dump2_by_vid.keys()
    changes['REMOVED'] = [dump1_by_vid[vid] for vid in removed_vids]
    if region_watched:
        common_vids = dump2_by_vid.keys() & dump1_by_vid.keys()
        common_public_vids = [vid for vid in common_vids if not is_video_private(dump2_by_vid[vid])]
        dump1_restricts = {vid: get_video_region_restriction(dump1_by_vid[vid], region_watched) for vid in common_public_vids}
        dump2_restricts = {vid: get_video_region_restriction(dump2_by_vid[vid], region_watched) for vid in common_public_vids}
        changes['REGION_RESTRICTION_CHANGE'] = {vid: (dump2_by_vid[vid], dump1_restricts[vid], dump2_restricts[vid]) for vid in common_public_vids
                                                if dump1_restricts[vid] != dump2_restricts[vid]}
    return changes


################################################################################
### JSON Dumps management

def dump_to_file(playlist, playlist_id, backup_dir):
    timestamp = time.strftime(ISO8601_TIMESTAMP_FORMAT, time.gmtime())
    filename = DUMP_FILENAME_TEMPLATE.format(playlist_id=playlist_id, timestamp=timestamp)
    filepath = os.path.join(backup_dir, filename)
    if os.path.exists(filepath):
        raise OSError('Dump file already exists: {}'.format(filepath))
    print('Dumping playlist to file: {}'.format(filename))
    with open(filepath, 'w+') as dump_file:
        json.dump(playlist, dump_file, sort_keys=True, indent=4)

def get_dumps(args):
    tagged_dump_filenames = get_tagged_dump_filenames(args.backup_dir, args.playlist_id)
    dump1 = get_dump_from_tag_or_timestamp(args.dump1_timestamp, tagged_dump_filenames, args)
    dump2 = get_dump_from_tag_or_timestamp(args.dump2_timestamp, tagged_dump_filenames, args)
    return dump1, dump2

def get_dump_from_tag_or_timestamp(dump_timestamp, tagged_dump_filenames, args):
    dump_filename = tagged_dump_filenames.get(dump_timestamp, None)
    if not dump_filename:
        if dump_timestamp in tagged_dump_filenames.keys():
            raise EnvironmentError("There isn't enough dump files in directory '{}'"
                                   " for playlist '{}' to use tag {}".format(args.backup_dir, args.playlist_id, dump_timestamp))
        dump_filename = find_dump_filename_for_timestamp(args.backup_dir, args.playlist_id, dump_timestamp)
    with open(dump_filename, 'r') as dump_file:
        return json.load(dump_file)

def get_tagged_dump_filenames(backup_dir, playlist_id):
    all_dumps = get_all_dumps_sorted_by_date(backup_dir, playlist_id)
    second_to_last_dump_timestamp = all_dumps[-2] if len(all_dumps) >= 2 else None
    last_dump_timestamp = all_dumps[-1] if len(all_dumps) >= 1 else None
    return dict((('LATEST', last_dump_timestamp), ('SECOND_TO_LAST', second_to_last_dump_timestamp)))

def get_all_dumps_sorted_by_date(backup_dir, playlist_id):
    file_pattern = DUMP_FILENAME_TEMPLATE.format(playlist_id=playlist_id, timestamp='*')
    # given the naming convention, lexicographical ordering is enough to sort by date
    return sorted(glob(os.path.join(backup_dir, file_pattern)))

def find_dump_filename_for_timestamp(backup_dir, playlist_id, timestamp_prefix):
    timestamp_prefix = ''.join(d for d in timestamp_prefix if d in string.digits)  # getting rid of any extra ponctuation
    file_pattern = DUMP_FILENAME_TEMPLATE.format(playlist_id=playlist_id, timestamp=timestamp_prefix + '*')
    file_matches = glob(os.path.join(backup_dir, file_pattern))
    if not file_matches:
        raise OSError('No dump file found for playlist "{}" in directory "{}"'
                      ' with a timestamp starting with {}'.format(playlist_id, backup_dir, timestamp_prefix))
    if len(file_matches) > 1:
        raise OSError(('Multiple files found for playlist "{}" in directory "{}" with a timestamp starting with {}\n'
                       'You may want to specify a timestamp more precisely').format(playlist_id, backup_dir, timestamp_prefix))
    return file_matches[0]


################################################################################
### Youtube Data API requests with progress bar

def get_playlist_with_progressbar(playlist_id):
    print('Getting all videos from Youtube playlist')
    paginated_playlist_iterator = list_playlist_videos_paginated(playlist_id)
    first_page = next(paginated_playlist_iterator)
    if 'error' in first_page:
        raise EnvironmentError(first_page)
    playlist = first_page['items']
    pages_count = math.floor(float(first_page['pageInfo']['totalResults']) / first_page['pageInfo']['resultsPerPage'])
    for page in tqdm(paginated_playlist_iterator, total=pages_count):
        playlist.extend(page['items'])
    return playlist

def list_playlist_videos_paginated(playlist_id):
    page_token = None
    while page_token is not False:
        response = requests.get('https://www.googleapis.com/youtube/v3/playlistItems', params={
            'key': YOUTUBE_API_KEY,
            'playlistId': playlist_id,
            'pageToken': page_token,
            'maxResults': PLAYLIST_ITEMS_REQUEST_BATCH_SIZE,
            'part': 'snippet',  # total quota cost: 2
        }).json()
        yield response
        page_token = response.get('nextPageToken', False)

def get_content_details_with_progressbar(playlist):
    print('Getting region restrictions for each video')
    video_ids = [item['snippet']['resourceId']['videoId'] for item in playlist]
    paginated_playlist_iterator = list_content_details_paginated(video_ids)
    content_details = []
    pages_count = math.floor(float(len(video_ids)) / CONTENT_DETAILS_REQUEST_BATCH_SIZE)
    for page in tqdm(paginated_playlist_iterator, total=pages_count):
        if 'error' in page:
            raise EnvironmentError(page)
        content_details.extend(page['items'])
    return content_details

def list_content_details_paginated(video_ids):
    batch_start_index = 0
    while batch_start_index < len(video_ids):
        videos_ids_batch = video_ids[batch_start_index:batch_start_index + CONTENT_DETAILS_REQUEST_BATCH_SIZE]
        response = requests.get('https://www.googleapis.com/youtube/v3/videos', params={
            'key': YOUTUBE_API_KEY,
            'id': ','.join(videos_ids_batch),  # it is not clearly documented, but the API does not accept more than 50 ids here
            'maxResults': CONTENT_DETAILS_REQUEST_BATCH_SIZE,
            'part': 'contentDetails',  # total quota cost: 2
        }).json()
        yield response
        batch_start_index += CONTENT_DETAILS_REQUEST_BATCH_SIZE

def add_content_details_to_playlist(content_details, playlist):
    private_videos_count = 0
    for index in range(len(playlist)):
        if not is_video_private(playlist[index]):
            playlist[index]['contentDetails'] = content_details[index - private_videos_count]['contentDetails']
        else:
            private_videos_count += 1


if __name__ == '__main__':
    main(sys.argv)
