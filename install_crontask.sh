#!/bin/bash
set -o pipefail -o errexit -o nounset

YPW_INSTALL_PATH="$(cd "$(dirname "${BASH_SOURCE[0]}" )" && pwd)"
cd "$YPW_INSTALL_PATH"

eval "$@"

: ${YOUTUBE_API_KEY:?'Required parameter'}
: ${EMAIL_DEST:?'Required parameter'}
: ${PLAYLIST_ID:?'Required parameter'}

echo -e "Creating youtube_playlist_watcher_crontask.sh with content:\n"

cat <<EOF | tee youtube_playlist_watcher_crontask.sh
#!/bin/bash
set -o pipefail -o errexit -o nounset
date
PLAYLIST_ID=$PLAYLIST_ID
EMAIL_SUBJECT="[YPW] Change detected in Youtube playlist \$PLAYLIST_ID"
ALERT_CMD="mail -s '\$EMAIL_SUBJECT' $EMAIL_DEST"
cd "$YPW_INSTALL_PATH"
./youtube_playlist_watcher.py --playlist-id \$PLAYLIST_ID dump --youtube-api-key $YOUTUBE_API_KEY && \\
    ./youtube_playlist_watcher.py --playlist-id \$PLAYLIST_ID purge-dumps && \\
    ./youtube_playlist_watcher.py --playlist-id \$PLAYLIST_ID compare --alert-cmd "\$ALERT_CMD"
EOF
chmod u+x youtube_playlist_watcher_crontask.sh

echo -e "\nCreating youtube_playlist_watcher_crontask with content:\n"

cat <<EOF | tee youtube_playlist_watcher_crontask
00 00 * * * root (cd "$YPW_INSTALL_PATH" && ./youtube_playlist_watcher_crontask.sh >> youtube_playlist_watcher_crontask.log 2>&1)
EOF

echo -e "\nMoving youtube_playlist_watcher_crontask into /etc/cron.d -> this requires sudo password:\n"
sudo mv youtube_playlist_watcher_crontask /etc/cron.d
