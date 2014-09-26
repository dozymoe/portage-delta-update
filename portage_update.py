import os
from re import compile as regex
from time import sleep

from helpers import force_directories
from helpers import timestamp_from_usr_portage, timestamp_from_tars
from helpers import validate_current_tarball, extract_rsync_tarball
from helpers import start_patching


# package dependencies

DEPENDS_ON = [
    "dev-util/diffball",
]

# exempted from rsync delete of /usr/portage

RSYNC_EXEMPT = ["/distfiles/", "/packages/"]

# const

PROJECT_DIR = os.path.realpath(os.path.dirname(__file__))
TARGET_DIR = "/usr/portage/"
TEMPORARY_DIR = "/tmp/"

PORTAGE_LIST_URL = "http://kambing.ui.ac.id/gentoo/releases/snapshots/current/"
PORTAGE_TAR_REGEX = regex(r"^portage-(?P<time>\d+)\.tar\.xz$")
PORTAGE_TAR_TEMPLATE = "portage-%i.tar.xz"

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
    portage_timestamp_tar = start_patching(
            PROJECT_DIR, portage_timestamp_tar, url=PORTAGE_DELTA_URL,
            temp_dir=TEMPORARY_DIR, tar_template=PORTAGE_TAR_TEMPLATE,
            regex=PORTAGE_DELTA_REGEX, template=PORTAGE_DELTA_TEMPLATE,
    )

# extract tarball to /usr/portage

if portage_timestamp_tar > portage_timestamp_current:
    force_directories(TARGET_DIR)
    extract_rsync_tarball(PROJECT_DIR, portage_timestamp_tar, TARGET_DIR,
                          temp_dir=TEMPORARY_DIR, rsync_exempt=RSYNC_EXEMPT,
                          template=PORTAGE_TAR_TEMPLATE)
