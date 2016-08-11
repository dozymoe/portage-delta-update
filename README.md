portage-delta-update
=====================

Python scripts to help update portage, a Gentoo software packaging system,
using the delta files instead of the usual rsync.

Warning: this method will give you late by 2-3 days portage tree, compared
to the usual rsync.

On the good side though, you can update portage tree as often as every day
without worrying about giving too much burden to the portage mirrors.

One delta file is usually 100K-600K bytes.

You first need to download timestamped snapshot file and save it in
/var/tmp/portage, *uncompressed*, for example:
/var/tmp/portage/portage-20160809.tar.

Then run ./configure.sh and use virtualenv to run the main file.

For example:

    #!/bin/bash
    (
        cd .
        . .virtualenv/bin/activate
        ./main.py
        deactivate
    )
