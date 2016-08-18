#!/usr/bin/env python

import os
import sys
from re import compile as regex
from host_helper import *
from local_helper import *
from portage_helper import *


DEPENDS_ON = [
    ('/usr/bin/patcher', 'dev-util/diffball'),
]

CONFIG = {
    'path': {
        'project': os.path.dirname(os.path.realpath(__file__)),
        'archives': '/var/tmp/portage/',
        'target': '/usr/portage/',
        'tarmount': '/mnt/portage/',
        'temp': '/tmp/',
    },
    'host': {
        'list': {
            'url': 'http://distfiles.gentoo.org/releases/' +\
                   'snapshots/current/',
            'regex': regex(r'^portage-(?P<time>\d+)\.tar\.bz2$'),
        },
        'delta': {
            'url': 'http://distfiles.gentoo.org/releases/' +\
                    'snapshots/current/deltas/',
            'regex': regex(r'^snapshot-(?P<time_f>\d+)-' +\
                   r'(?P<time_t>\d+)\.patch\.bz2$'),
            'template': 'snapshot-%i-%i.patch.bz2',
        },
    },
    'local': {
        'regex': regex(r'^portage-(?P<time>\d+)\.tar$'),
        'template': 'portage-%i.tar',
    },
    'rsync': {
        'exclude': ('/distfiles/***', '/local/***', '/packages/***'),
    },
    'target': {
        'exclude': ('distfiles', 'local', 'packages'),
    },
}

def start_patching():
    time = timestamp_from_downloaded_tars(CONFIG)
    patches = set(get_deltas(CONFIG, time))

    # applying patches
    for time_f, time_t in patches:
        if time != time_f:
            sys.stderr.write(('Patch for %i is not compatible ' +
                    'with our %i\n') % (time_f, time))
            continue

        download_patch(CONFIG, time_f, time_t)
        apply_patch(CONFIG, time_f, time_t)
        time = time_t


def extract_tarball():
    time = timestamp_from_downloaded_tars(CONFIG)
    time_c = timestamp_from_portage(CONFIG)

    if time <= time_c:
        return

    clean_target(CONFIG)
    untar_tarball(CONFIG, time)

    ## extract tarball to /usr/portage
    #if not mount_tarball(CONFIG, time):
    #    sys.stderr.write('Mount tarball failed\n')
    #    return
    #
    #try:
    #    rsync_tarball(CONFIG)
    #    os.system('eix-update')
    #finally:
    #    umount_tarball(CONFIG)


start_patching()
extract_tarball()
