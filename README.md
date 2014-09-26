portage-delta-upgrade
=====================

Python scripts to help upgrade portage, a Gentoo software packaging system,
using the delta files instead of the usual rsync.

Warning: this method will give you late by 2-3 days portage tree, compared
to the usual rsync.

On the good side though, you can update portage tree as often as every day
without worrying about giving too much burden to the portage mirrors.

One delta file is usually 100K-600K bytes.

PS: eh, the main file is `portage_update.py`
