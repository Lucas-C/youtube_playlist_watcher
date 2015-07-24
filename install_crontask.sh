#!/bin/bash
set -o pipefail -o errexit -o nounset

YPW_INSTALL_PATH="$(cd "$(dirname "${BASH_SOURCE[0]}" )" && pwd)"

eval "$@"

: ${YOUTUBE_API_KEY:?'Required parameter'}
: ${EMAIL_DEST:?'Required parameter'}
: ${PLAYLIST_ID:?'Required parameter'}

echo -e "Creating $YPW_INSTALL_PATH/youtube_playlist_watcher_crontask.sh with content:\n"

cat <<EOF | tee $YPW_INSTALL_PATH/youtube_playlist_watcher_crontask.sh
#!/bin/bash
set -o pipefail -o errexit -o nounset
SCRIPT_DIR="\$(cd "\$(dirname "\${BASH_SOURCE[0]}" )" && pwd)"
cd \$SCRIPT_DIR
export YOUTUBE_API_KEY=$YOUTUBE_API_KEY
EMAIL_DEST=$EMAIL_DEST
PLAYLIST_ID=$PLAYLIST_ID
EMAIL_SUBJECT="[YPW] Change detected in Youtube playlist \$PLAYLIST_ID"
ALERT_CMD="mail -s \$EMAIL_SUBJECT \$EMAIL_DEST"
./youtube_playlist_watcher.py --playlist-id \$PLAYLIST_ID dump && \\
    ./youtube_playlist_watcher.py --playlist-id \$PLAYLIST_ID purge-dumps && \\
    ./youtube_playlist_watcher.py --playlist-id \$PLAYLIST_ID compare --alert-cmd \$ALERT_CMD
EOF

echo -e "\nCreating /etc/cron.d/youtube_playlist_watcher_crontask with content:\n(This require sudo permission)\n"

cat <<EOF | sudo tee /etc/cron.d/youtube_playlist_watcher_crontask
00 00 * * * root (cd $YPW_INSTALL_PATH && ./youtube_playlist_watcher_crontask.sh) >> youtube_playlist_watcher_crontask.log 2>&1
EOF

