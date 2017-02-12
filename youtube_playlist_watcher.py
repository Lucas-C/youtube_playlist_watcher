#!/usr/bin/env python3.4

import argparse, json, math, os, requests, string, subprocess, sys, time, traceback
from os.path import basename
from glob import glob
from tqdm import tqdm
from urllib.parse import urlencode

DUMP_FILENAME_TEMPLATE = 'youtube-playlist-{playlist_id}-{timestamp}.json'
ISO8601_TIMESTAMP_FORMAT = '%Y%m%d%H%M%S'
PLAYLIST_ITEMS_REQUEST_BATCH_SIZE = 50
VIDEOS_DETAILS_REQUEST_BATCH_SIZE = 50
THIS_SCRIPT_PARENT_DIR = os.path.dirname(os.path.realpath(__file__))

def main(argv):
    args = parse_args(argv[1:])
    args.exec_cmd(args)

################################################################################
### CLI arguments parsing

def parse_args(argv):
    parser = argparse.ArgumentParser(description='Dump & compare the content of Youtube playlists',
                                     fromfile_prefix_chars='@',
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
                                choices=SublistChoices(('ADDED', 'REMOVED', 'DELETED', 'IS_PRIVATE', 'IS_BLOCKED_IN_REGION')),
                                default=('DELETED', 'IS_PRIVATE', 'IS_BLOCKED_IN_REGION'),
                                help='Comma-separated list of changes that trigger the "alert-cmd"')
    compare_parser.add_argument('--region-watched', default='FR', help='Region watched for restrictions changes')
    compare_parser.add_argument('--alert-cmd', help='Command to run when a change is detected')
    dump_parser = subparsers.add_parser('dump', formatter_class=ArgparseHelpFormatter)
    dump_parser.set_defaults(exec_cmd=dump_command)
    dump_parser.add_argument('--youtube-api-key', required=True)
    purge_dumps_parser = subparsers.add_parser('purge-dumps', formatter_class=ArgparseHelpFormatter)
    purge_dumps_parser.add_argument('--keep-count', type=int, default=50, help='Number of JSON dumps to keep')
    purge_dumps_parser.set_defaults(exec_cmd=purge_dumps_command)
    return parser.parse_args(argv)

class SublistChoices(set):
    def __contains__(self, l):
        return set(l).issubset(self)

class ArgparseHelpFormatter(argparse.RawTextHelpFormatter, argparse.ArgumentDefaultsHelpFormatter):
    pass


################################################################################
### Main CLI commands

def dump_command(args):
    playlist = get_playlist_with_progressbar(args.youtube_api_key, args.playlist_id)
    videos_details = get_videos_details_with_progressbar(args.youtube_api_key, playlist)
    add_videos_details_to_playlist(videos_details, playlist)
    dump_to_file(playlist, args.playlist_id, args.backup_dir)

def purge_dumps_command(args):
    all_dumps = get_all_dumps_sorted_by_date(args.backup_dir, args.playlist_id)
    dumps_to_remove = all_dumps[:-args.keep_count]
    if not dumps_to_remove:
        return
    print('Now removing the following dumps: {}'.format(' '.join([basename(f) for f in dumps_to_remove])))
    for dump in dumps_to_remove:
        os.unlink(dump)

def compare_command(args):
    try:
        _compare_command(args)
    except Exception:
        if args.alert_cmd:
            error_msg = ''.join(traceback.format_exception(*sys.exc_info()))
            print(system_command(args.alert_cmd, error_msg))
        raise

def _compare_command(args):
    dump1, dump2 = get_dumps(args)
    changes = get_changes(dump1, dump2, args.region_watched)
    if not any(changes.values()):
        return
    text_output = make_text_output(args, changes)
    print(text_output)
    alerting_changes = {type: items for (type, items) in changes.items() if type in args.alert_on and items}
    if alerting_changes and args.alert_cmd:
        print(system_command(args.alert_cmd, text_output))

################################################################################
### Video items utility functions

def get_video_id(item):
    return item['snippet']['resourceId']['videoId']

def get_video_url(item):
    return 'https://www.youtube.com/watch?v=' + get_video_id(item)

def get_video_name(item):
    return item['snippet']['title']

def get_search_url(video_name):
    return 'https://www.youtube.com/results?' + urlencode({'search_query': video_name})

def is_video_deleted(item):
    snippet = item.get('snippet', None)
    if snippet and snippet['title'] == 'Deleted video' and snippet['description'] == 'This video is unavailable.':
        return True
    if 'status' in item:
        return item['status']['uploadStatus'] != 'processed'
    return False

def is_video_private(item):
    # Alt: retrieve the 'status' part (quota cost 2) -> item['status']['privacyStatus'] == 'private'
    if item['snippet']['description'] != 'This video is private.' and item['snippet']['title'] != 'Private video':
        return False
    if item['snippet']['description'] != 'This video is private.' or item['snippet']['title'] != 'Private video':
        raise EnvironmentError('Youtube Data API change detected')
    return True

def is_video_blocked_in_region(item, region):
    try:
        region_restriction = item['contentDetails']['regionRestriction']
    except KeyError:
        return False
    if region in region_restriction.get('blocked', []):
        return True
    if 'allowed' in region_restriction:
        return region not in region_restriction['allowed']
    return False


################################################################################
### Textual output generation

def make_text_output(args, changes):
    header = '[YPW] Changes detected in playlist https://www.youtube.com/playlist?list={} (region watched: {})'.format(
            args.playlist_id, args.region_watched)
    output_lines_iterator = (list(getattr(OutputLinesIterator, changetype.lower())(changeset, args)) for (changetype, changeset) in changes.items())
    return '\n'.join(sum(output_lines_iterator, [header]))

class OutputLinesIterator:
    @staticmethod
    def added(changeset, *_):
        for new_item in changeset:
            yield 'ADDED: ' + get_video_name(new_item) + ' ' + get_video_url(new_item)
    @staticmethod
    def removed(changeset, *_):
        for old_item in changeset:
            video_name = get_video_name(old_item)
            yield ('REMOVED: ' + video_name + ' ' + get_video_url(old_item)
                 + '\n -> find another video named like that: ' + get_search_url(video_name))
    @staticmethod
    def deleted(changeset, *_):
        for old_item in changeset:
            video_name = get_video_name(old_item)
            yield ('DELETED: ' + get_video_name(old_item) + ' ' + get_video_url(old_item)
                 + '\n -> find another video named like that: ' + get_search_url(video_name))
    @staticmethod
    def is_blocked_in_region(changeset, *_):
        for new_item, region in changeset:
            video_name = get_video_name(old_item)
            yield ('IS BLOCKED IN REGION "' + region + '" : ' + get_video_name(new_item) + ' ' + get_video_url(new_item)
                 + '\n  (you can still access this video and quickly remove it from your playlist from the drop-down menu under its title)'
                 + '\n -> find another video named like that: ' + get_search_url(video_name))
    @staticmethod
    def is_private(changeset, args):
        for old_item in changeset:
            video_name = get_video_name(old_item) if not is_video_private(old_item) else retrieve_video_name_from_prev_dumps(get_video_id(old_item), args)
            yield ('IS PRIVATE: ' + video_name + ' ' + get_video_url(old_item)
                 + '\n -> find another video named like that: ' + get_search_url(video_name))

def retrieve_video_name_from_prev_dumps(video_id, args):
    for dump in get_all_dumps_contents_sorted_by_date(args.backup_dir, args.playlist_id):
        try:
            prev_same_video = next(item for item in dump if get_video_id(item) == video_id)
        except StopIteration:
            return ''
        if not is_video_private(prev_same_video):
            return get_video_name(prev_same_video)
    return ''


################################################################################
### Changes detection

def get_changes(dump1, dump2, region_watched):
    changes = {}
    dump1_by_vid = {get_video_id(item): item for item in dump1}
    dump2_by_vid = {get_video_id(item): item for item in dump2}
    common_vids = [(dump1_by_vid[vid], dump2_by_vid[vid]) for vid in set(dump2_by_vid.keys())&set(dump1_by_vid.keys())]
    changes['IS_PRIVATE'] = [old_item for (old_item, new_item) in common_vids if is_video_private(new_item)]
    added_vids = dump2_by_vid.keys() - dump1_by_vid.keys()
    changes['ADDED'] = [dump2_by_vid[vid] for vid in added_vids]
    removed_vids = dump1_by_vid.keys() - dump2_by_vid.keys()
    def should_ignore_removed_video(item):
        return any([
            region_watched and is_video_blocked_in_region(item, region_watched),
            is_video_private(item),
            is_video_deleted(item),
        ])
    changes['REMOVED'] = [dump1_by_vid[vid] for vid in removed_vids if not should_ignore_removed_video(dump1_by_vid[vid])]
    changes['DELETED'] = [dump1_by_vid[vid] for vid in dump2_by_vid.keys() if is_video_deleted(dump2_by_vid[vid])]
    if region_watched:
        changes['IS_BLOCKED_IN_REGION'] = [(item, region_watched) for item in dump2 if is_video_blocked_in_region(item, region_watched)]
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

def get_all_dumps_contents_sorted_by_date(backup_dir, playlist_id):
    for dump_path in get_all_dumps_sorted_by_date(backup_dir, playlist_id):
        with open(dump_path, 'r') as dump_file:
            yield json.load(dump_file)

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

def get_playlist_with_progressbar(youtube_api_key, playlist_id):
    print('Getting all videos from Youtube playlist')
    paginated_playlist_iterator = list_playlist_videos_paginated(youtube_api_key, playlist_id)
    first_page = next(paginated_playlist_iterator)
    if 'error' in first_page:
        raise EnvironmentError(first_page)
    playlist = first_page['items']
    pages_count = math.floor(float(first_page['pageInfo']['totalResults']) / first_page['pageInfo']['resultsPerPage'])
    for page in tqdm(paginated_playlist_iterator, total=pages_count):
        playlist.extend(page['items'])
    return playlist

def list_playlist_videos_paginated(youtube_api_key, playlist_id):
    page_token = None
    while page_token is not False:
        response = requests.get('https://www.googleapis.com/youtube/v3/playlistItems', params={
            'key': youtube_api_key,
            'playlistId': playlist_id,
            'pageToken': page_token,
            'maxResults': PLAYLIST_ITEMS_REQUEST_BATCH_SIZE,
            'part': 'snippet',  # total quota cost: 1 (base) + 2
        }).json()
        yield response
        page_token = response.get('nextPageToken', False)

def get_videos_details_with_progressbar(youtube_api_key, playlist):
    print('Getting region restrictions for each video')
    video_ids = [item['snippet']['resourceId']['videoId'] for item in playlist]
    paginated_playlist_iterator = list_videos_details_paginated(youtube_api_key, video_ids)
    videos_details = []
    pages_count = math.floor(float(len(video_ids)) / VIDEOS_DETAILS_REQUEST_BATCH_SIZE)
    for page in tqdm(paginated_playlist_iterator, total=pages_count):
        if 'error' in page:
            raise EnvironmentError(page)
        videos_details.extend(page['items'])
    return videos_details

def list_videos_details_paginated(youtube_api_key, video_ids):
    batch_start_index = 0
    while batch_start_index < len(video_ids):
        videos_ids_batch = video_ids[batch_start_index:batch_start_index + VIDEOS_DETAILS_REQUEST_BATCH_SIZE]
        response = requests.get('https://www.googleapis.com/youtube/v3/videos', params={
            'key': youtube_api_key,
            'id': ','.join(videos_ids_batch),  # it is not clearly documented, but the API does not accept more than 50 ids here
            'maxResults': VIDEOS_DETAILS_REQUEST_BATCH_SIZE,
            'part': 'contentDetails,status',  # total quota cost: 1 (base) + 2 + 2
        }).json()
        yield response
        batch_start_index += VIDEOS_DETAILS_REQUEST_BATCH_SIZE

def add_videos_details_to_playlist(videos_details, playlist):
    skipped_videos_count = 0
    for index, video_item in enumerate(playlist):
        video_details = videos_details[index - skipped_videos_count]
        if is_video_private(video_item) or is_video_deleted(video_item):
            skipped_videos_count += 1
        else:
            video_item.update(video_details)

def system_command(command, stdin):
    return subprocess.check_output(command, input=bytes(stdin, 'UTF-8'), shell=True, stderr=subprocess.STDOUT).decode("utf-8")


if __name__ == '__main__':
    main(sys.argv)
