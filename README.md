Do you get frustrated by videos disappearing from you Youtube playlist,
because of copyright infringement, new region restrictions or just because the guy who uploaded them removed it,
with no way for you to find out which where those clips ?

Because Youtube does not keep trace of those dead videos,
your only chance to recall what were their names is a Google search based on their video ids.

But no more !

This Python script will keep track of your playlist metadata,
detect changes like disappearing videos,
and alert you with emails like this:

    SUBJECT: [YPW] Change detected in Youtube playlist FLF8xTv55ZmwikWWmWLPEAZQ
    Playlist: https://www.youtube.com/playlist?list=FLF8xTv55ZmwikWWmWLPEAZQ
    REGION RESTRICTIONS CHANGED for Sade - The Best Of Sade | Full Album : {"blocked": ["DE"]}-> {}
    BECAME PRIVATE: https://www.youtube.com/watch?v=T4ZCJzjufYs
    REMOVED: The Cure - Burn 1994 HQ (The Crow) -> find another video named like that: https://www.youtube.com/results?search_query=The+Cure+-+Burn+1994+HQ+%28The+Crow%29

![](https://chezsoi.org/lucas/wwcb/photos/NinjaTurtlesPowerRangers.gif)


## Requirements
A machine with:

- Python 3.4 at least
- the ability to run daily jobs (e.g. standard Linux cron jobs)
- `mail`, `mutt` or any other command-line email client

and a [Youtube Data API key](https://developers.google.com/youtube/v3/getting-started).


## Installation

Download the Python script, make it executable and install the required Python dependencies:

    pip3.4 install --user -r requirements.txt

Then just define a daily cron job and its dedicated Bash script
(just substitute the `...` by real values before running those commands) :

    cd /path/to/ypw # where you downloaded the script and the JSON dumps will get stored
    ./install_crontask.sh YOUTUBE_API_KEY=... EMAIL_DEST=... PLAYLIST_ID=...

This script will generate the `youtube_playlist_watcher_crontask.sh` script that will be invoked by the cron job.
If you want to watch multiple playlists, simply repeat its last lines with a different playlist id.


## Manual usage

To compare a dump taken at any date with the latest one:

    YOUTUBE_API_KEY=...
    ./youtube_playlist_watcher.py --playlist $PLAYLIST_ID compare 2015-01-01 LATEST

Want to find more secret features ? The `--help` flag is your friend.

Or use the power Luke: READ THE SOURCE !


## Contributing

Bug reports or features suggestions are warmly welcome !

For the devs:

    pip3.4 install --user -r dev-requirements.txt
    pre-commit install
