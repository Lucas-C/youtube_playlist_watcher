#!/bin/bash
set -o pipefail -o errexit -o nounset

YPW_INSTALL_PATH="$(cd "$(dirname "${BASH_SOURCE[0]}" )" && pwd)"
SHELL_RC_FILE=~/.bashrc

eval "$@"

: ${YOUTUBE_API_KEY:?'Required parameter'}
: ${PLAYLIST_ID:?'Required parameter'}

echo -e "Adding the following to your $SHELL_RC_FILE to display a YPW report once per day, the 2nd time a terminal opens:"

# Removing any existing YPW bashrc config so this script is idempotent
sed -i '/#--YPW-START--#/,/#--YPW-END--#/d' $SHELL_RC_FILE

cat <<EOF | tee -a $SHELL_RC_FILE
#--YPW-START--#

ypw_check () {
    local playlist_id=\${1:-$PLAYLIST_ID}
    cd "$YPW_INSTALL_PATH"
    ./youtube_playlist_watcher.py --playlist-id \$playlist_id dump --youtube-api-key $YOUTUBE_API_KEY \\
        && ./youtube_playlist_watcher.py --playlist-id \$playlist_id purge-dumps \\
        && ./youtube_playlist_watcher.py --playlist-id \$playlist_id compare --alert-cmd 'cat > ~/.ypw_last_report' \\
        || rm ~/.ypw_last_report # in case of failure (e.g. no Internet connexion) we allow new attempts later today
    cd - # back to initial cwd
}

was_edited_today () {
    test \$((\$(stat --format "%Y" "\$1") / 86400)) = \$((\$(date "+%s") / 86400))
}

if [ -s ~/.ypw_last_report ] && ! tail -n 1 ~/.ypw_last_report | grep -qF 'this report was displayed in shell'; then
    cat ~/.ypw_last_report
    echo '(this report is kept at ~/.ypw_last_report)'
    date "+(this report was displayed in shell on %c)" >> ~/.ypw_last_report
elif ! [ -e ~/.ypw_last_report ] || ! was_edited_today ~/.ypw_last_report; then
    echo -n > ~/.ypw_last_report  # This ensures no other report generation will be launched today
    echo "[YPW] Generating Youtube Playlist Watcher report in background"
    ypw_check >~/.ypw_output.log 2>&1 &
fi

#--YPW-END--#
EOF
