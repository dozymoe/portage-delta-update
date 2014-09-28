import os
from re import compile as regex
from time import sleep

from helpers import force_directories
from helpers import timestamp_from_usr_portage, timestamp_from_tars
from helpers import validate_current_tarball, extract_rsync_tarball
from helpers import perform_before_patch, start_patching, perform_after_patch


# package dependencies

DEPENDS_ON = [
    ("/usr/bin/patcher", "dev-util/diffball"),
]

# exempted from rsync delete of /usr/portage

RSYNC_EXEMPT = ["/distfiles/", "/local/", "/packages/"]

# const

PROJECT_DIR = os.path.realpath(os.path.dirname(__file__))
TARGET_DIR = "/usr/portage/"
TEMPORARY_DIR = "/tmp/"

PORTAGE_LIST_URL = "http://kambing.ui.ac.id/gentoo/releases/snapshots/current/"
PORTAGE_TAR_REGEX = regex(r"^portage-(?P<time>\d+)\.tar\.bz2$")
PORTAGE_TAR_TEMPLATE = "portage-%i.tar.bz2"

PORTAGE_DELTA_URL = PORTAGE_LIST_URL + "deltas/"
PORTAGE_DELTA_REGEX = regex(r"^snapshot-(?P<time_f>\d+)-(?P<time_t>\d+)\.patch\.bz2$")
PORTAGE_DELTA_TEMPLATE = "snapshot-%i-%i.patch.bz2"

# vars

portage_timestamp_current = timestamp_from_usr_portage(TARGET_DIR)
portage_timestamp_tar = timestamp_from_tars(PROJECT_DIR, 
                                            regex=PORTAGE_TAR_REGEX,
                                            template= PORTAGE_TAR_TEMPLATE)

# fetch portage list

latest_timestamp, portage_timestamp_tar = validate_current_tarball(
        PROJECT_DIR, portage_timestamp_tar,
        url=PORTAGE_LIST_URL,
        temp_dir=TEMPORARY_DIR,
        regex=PORTAGE_TAR_REGEX, template=PORTAGE_TAR_TEMPLATE
)

# retry failed tarball download

retry = 1
while retry and portage_timestamp_tar == 0:
    sleep(5)
    latest_timestamp, portage_timestamp_tar = validate_current_tarball(
            PROJECT_DIR, portage_timestamp_tar,
            url=PORTAGE_LIST_URL,
            temp_dir=TEMPORARY_DIR,
            regex=PORTAGE_TAR_REGEX, template=PORTAGE_TAR_TEMPLATE,
    )

# download patches

if latest_timestamp > portage_timestamp_tar:
    if not perform_before_patch(PROJECT_DIR, portage_timestamp_tar, TEMPORARY_DIR,
                                PORTAGE_TAR_TEMPLATE):
        exit(-1)
    portage_timestamp_tar = start_patching(
            TEMPORARY_DIR, portage_timestamp_tar, url=PORTAGE_DELTA_URL,
            tar_template=PORTAGE_TAR_TEMPLATE,
            regex=PORTAGE_DELTA_REGEX, template=PORTAGE_DELTA_TEMPLATE,
    )
    perform_after_patch(PROJECT_DIR, portage_timestamp_tar, TEMPORARY_DIR,
                        PORTAGE_TAR_TEMPLATE)

# extract tarball to /usr/portage

import pudb; pudb.set_trace()

if portage_timestamp_tar > portage_timestamp_current:
    force_directories(TARGET_DIR)
    extract_rsync_tarball(PROJECT_DIR, portage_timestamp_tar, TARGET_DIR,
                          temp_dir=TEMPORARY_DIR, rsync_exempt=RSYNC_EXEMPT,
                          template=PORTAGE_TAR_TEMPLATE)
