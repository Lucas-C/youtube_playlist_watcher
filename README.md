Do you get frustrated by videos disappearing from your Youtube playlist,
because of copyright infringement, new region restrictions or just because the guy who uploaded them removed it ?
With no way for you to find out which where those clips:
because Youtube does not keep trace of those dead videos,
your only chance to recall what were their names is a Google search based on their video ids.

But no more !

This Python script will keep JSON backups of your playlists on your computer,
detect changes like disappearing videos,
and alert you with console messages or emails like this:

    SUBJECT: [YPW] Change detected in Youtube playlist FLF8xTv55ZmwikWWmWLPEAZQ
    Playlist: https://www.youtube.com/playlist?list=FLF8xTv55ZmwikWWmWLPEAZQ
    REGION RESTRICTIONS CHANGED for Sade - The Best Of Sade | Full Album : {"blocked": ["DE"]}-> {} https://www.youtube.com/watch?v=zX8nZI8U9XY
    -> find another video named like that: https://www.youtube.com/results?search_query=Sade+-+The+Best+Of+Sade+%7C+Full+Album
    BECAME PRIVATE: https://www.youtube.com/watch?v=T4ZCJzjufYs
    -> find another video named like that: https://www.youtube.com/results?search_query=Patrick+Bruel+%22J%27te+l%27dis+quand+m%C3%AAme%22
    DELETED: The Cure - Burn 1994 HQ (The Crow)
    -> find another video named like that: https://www.youtube.com/results?search_query=The+Cure+-+Burn+1994+HQ+%28The+Crow%29

![](https://chezsoi.org/lucas/wwcb/photos/NinjaTurtlesPowerRangers.gif)


## Requirements
A computer with:

- Python 3.4 at least
- a [Youtube Data API key](https://developers.google.com/youtube/v3/getting-started) (it's free)
- and either:
    * the ability to run daily jobs (e.g. standard Linux cron jobs) + `mail`, `mutt` or any other command-line email client
    * a Bash-based console (Cygwin is ok) that you open frequently, so you'll see the reports inside


## Installation in .bashrc to get reports in your temrinal

If installed this way, YPW will do the following:
- each time you'll open a new terminal, it'll check if it has already been executed today,
and else launch a background task to dump & check your playlist for changes.
- the next time you'll open a console after this task completed,
you'll see the report at the top of your terminal (it can be empty if no changes were detected).

To install it, run the following in a console (just remember to substitute the `...` on the last line by real values) :

    cd /path/to/your/installation/directory # the JSON dumps will be stored there by default
    wget https://rawgit.com/Lucas-C/youtube_playlist_watcher/master/youtube_playlist_watcher.py
    wget https://rawgit.com/Lucas-C/youtube_playlist_watcher/master/install_bashrc_banner.sh
    chmod u+x *.sh *.py
    pip3.4 install --user requests tqdm
    ./install_bashrc_banner.sh YOUTUBE_API_KEY=... PLAYLIST_ID=...

This last script will append some lines to your ~/.bashrc, that implement the logic detailed above.
It will also define a `ypw_check` shell function that you can invoke manually if you want.

If you want to watch multiple playlists, keep more or less JSON dumps in history
or change the kind of playlist changes watched, simply edit this section of your ~/.bashrc manually.


## Installation as a cron job sending emails

Run the following in a console (just remember to substitute the `...` on the last line by real values) :

    cd /path/to/your/installation/directory # the JSON dumps will be stored there by default
    wget https://rawgit.com/Lucas-C/youtube_playlist_watcher/master/youtube_playlist_watcher.py
    wget https://rawgit.com/Lucas-C/youtube_playlist_watcher/master/install_crontask.sh
    chmod u+x *.sh *.py
    pip3.4 install --user requests tqdm
    ./install_crontask.sh YOUTUBE_API_KEY=... PLAYLIST_ID=... EMAIL_DEST=...

This last script will generate a `youtube_playlist_watcher_crontask.sh` script that will be invoked by a cron job,
running every day at midnight.

If you want to watch multiple playlists, use another email client command (the default is `mail`),
keep more or less JSON dumps in history or change the kind of playlist changes watched,
simply edit this file manually.


## Python script manual usage

To compare a dump taken at any date with the latest one:

    ./youtube_playlist_watcher.py --playlist $playlist_id compare 2015-01-01 LATEST

Want to find more secret features ? The `--help` flag is your friend.

Or use the power Luke: READ THE SOURCE !


## Contributing

Bug reports or features suggestions are warmly welcome !

For the devs:

    pip3.4 install --user pre-commit
    pre-commit install
