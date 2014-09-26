import os
import sh
import sys
from BeautifulSoup import BeautifulSoup
from dateutil.parser import parse as parse_datetime
from hashlib import md5
from requests import get as http_get

def file_md5(filename):
    hasher = md5()
    with open(filename, 'rb') as f:
        buf = f.read(65536)
        while len(buf) > 0:
            hasher.update(buf)
            buf = f.read(65536)
    return hasher.hexdigest()

def force_directories(*args, **kwargs):
    for path in args:
        # remove directory
        if kwargs.get("purge", False) and os.path.exists(path):
            sh.rm(path, "-r")
        # create new directory if not exist
        if not os.path.exists(path):
            os.makedirs(path)

def timestamp_from_usr_portage(path):
    filename = os.path.join(path, "metadata", "timestamp")
    if os.path.exists(filename):
        with open(filename, "r") as f:
            time = parse_datetime(f.readline().strip())
            return int(time.strftime("%Y%m%d"))
    return 0

def timestamp_from_tars(path, regex, template):
    time = 0
    for f in os.listdir(path):
        match = regex.search(f)
        if not match:
            continue
        time_l = int(match.group("time"))

        # auto remove older tar balls
        if time_l < time:
            os.unlink(os.path.join(path, template % time_l))
        # accept newer tar balls
        elif time_l > time:
            time = time_l
    return time

def validate_current_tarball(path, time, url, temp_dir, regex, template):
    latest = 0
    new_time = 0
    download = True
    response = http_get(url)
    soup = BeautifulSoup(response.text)

    for l in soup.findAll("a"):
        match = regex.search(l.text)
        if not match:
            continue
        time_l = int(match.group("time"))

        # is it newer
        if time_l > latest:
            latest = time_l
        # is this our current
        if time_l == time:
            new_time = time
            download = False

    if latest == 0:
        sys.stderr.write("Can't find any tarballs in %s\n" % url)
        return (0, 0)

    if new_time == 0:
        new_time = latest

    filename = template % new_time

    if download:
        # download new tar ball
        filepath = os.path.join(temp_dir, filename)
        response = http_get(os.path.join(url, filename), stream=True)

        with open(filepath, "wb") as f:
            for chunk in response.iter_content(65536):
                f.write(chunk)
    else:
        filepath = os.path.join(path, filename)

    # check md5
    response = http_get(url + filename + ".md5sum").text
    md5sum = response[:response.index(" ")]

    if md5sum != file_md5(filename):
        # failed md5 test
        return (0, 0)
    elif download:
        # copy downloaded file from /tmp/ directory to project directory
        os.rename(filepath, os.path.join(path, filename))

    return (latest, new_time)

def start_patching(path, time, url, temp_dir, regex, template, tar_template):
    # applying patches and renaming our portage file
    patches = set()
    response = http_get(url)
    soup = BeautifulSoup(response.text)

    for l in soup.findAll("a"):
        match = regex.search(l.text)
        if not match:
            continue
        time_f = int(match.group("time_f"))

        # accept if `from time` is equal or later than ours
        if time_f >= time:
            patches.add((time_f, int(match.group("time_t"))))

    for time_f, time_t in patches:
        if time != time_f:
            sys.stderr.write("Patch for %i is not compatible "
                             "with our %i\n" % (time_f, time))
            continue
        time = apply_patch(path, time_f, time_t, url, temp_dir, regex,
                           template, tar_template)
    return time

def apply_patch(path, time_f, time_t, url, temp_dir, regex, template,
                tar_template):
    # download compressed patch
    filename = template % (time_f, time_t)
    filepath = os.path.join(temp_dir, filename)
    response = http_get(os.path.join(url, filename), stream=True)

    with open(filepath, "wb") as f:
        for chunk in response.iter_content(65536):
            f.write(chunk)

    # check md5
    response = http_get(url + filename + ".md5sum").text
    md5sum = response[:response.index(" ")]
    if md5sum != file_md5(filename):
        return time_f

    # do patch
    from_file = os.path.join(path, tar_template % time_f)
    to_file = os.path.join(temp_dir, tar_template % time_f)
    if not sh.patcher(from_file, filepath, to_file):
        sh.rm(from_file)
        os.rename(to_file, os.path.join(path, tar_template % time_t))
        return time_t
    return time_f

def extract_rsync_tarball(path, time, target_dir, temp_dir, template,
                          rsync_exempt):
    build_dir = os.path.join(temp_dir, "portage_update_build")
    force_directories(build_dir, purge=True)

    sh.tar("-xp", file=os.path.join(path, template % time),
           directory=build_dir)

    exempteds = ('--exclude="%s"' % x for x in rsync_exempt)
    sh.rsync(os.path.join(build_dir, ""), os.path.join(target_dir, ""), "-av",
             "--delete", " ".join(exempteds))
