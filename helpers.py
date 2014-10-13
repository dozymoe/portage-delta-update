import os
import sh
import sys
from BeautifulSoup import BeautifulSoup
from datetime import datetime
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
    filename = os.path.join(path, "metadata", "timestamp.x")
    if os.path.exists(filename):
        with open(filename, "r") as f:
            time_str = f.readline()
            time_str = time_str[:time_str.index(' ')]
            time = datetime.utcfromtimestamp(int(time_str))
            return int(time.strftime("%Y%m%d"))
    return 0

def timestamp_from_tars(path, regex, template):
    time = 0
    for f in os.listdir(path):
        match = regex.search(f)
        if not match:
            continue
        time_l = int(match.group("time"))

        if time_l < time:
            # auto remove older tar balls
            os.unlink(os.path.join(path, template % time_l))
        elif time_l > time:
            # auto remove older tar balls
            if time > 0:
                os.unlink(os.path.join(path, template % time))
            # accept newer tar balls
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

    if md5sum != file_md5(filepath):
        # failed md5 test
        return (0, 0)
    elif download:
        # copy downloaded file from /tmp/ directory to project directory
        sh.mv(filepath, os.path.join(path, filename))

    return (latest, new_time)

def perform_before_patch(path, time, temp_dir, template):
    filename = template % time
    unc_filename, ext = os.path.splitext(filename)
    file_from = os.path.join(path, filename)
    file_to   = os.path.join(temp_dir, unc_filename)
    print("Copying {} to working directory".format(file_from))
    ret = sh.bunzip2(sh.cat(file_from), _out=file_to).exit_code
    return ret == 0

def start_patching(temp_dir, time, url, regex, template, tar_template):
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
        time = apply_patch(temp_dir, time_f, time_t, url, regex,
                           template, tar_template)
    return time

def apply_patch(temp_dir, time_f, time_t, url, regex, template, tar_template):
    # download compressed patch
    filename = template % (time_f, time_t)
    filepath = os.path.join(temp_dir, filename)
    response = http_get(os.path.join(url, filename), stream=True)

    print("Applying patch " + filename)
    with open(filepath, "wb") as f:
        for chunk in response.iter_content(65536):
            f.write(chunk)

    # check md5
    response = http_get(url + filename + ".md5sum").text
    md5sum = response[:response.index(" ")]
    if md5sum != file_md5(filepath):
        return time_f

    # do patch
    from_file = os.path.join(temp_dir, tar_template % time_f)
    to_file   = os.path.join(temp_dir, tar_template % time_t)
    # remove the .bz2 extension
    from_file, ext = os.path.splitext(from_file)
    to_file  , ext = os.path.splitext(to_file)
    # ToDo: this would raise exception >.>
    if sh.patcher(from_file, filepath, to_file).exit_code == 0:
        # successfully patched, keep new, delete old tarball
        os.remove(from_file)
        return time_t

    # returning the from-time will freeze the tarball to the latest working
    # patch, and stop iterating patches in `start_patching()`
    return time_f

def perform_after_patch(path, time, temp_dir, template):
    filename = template % time
    unc_filename, ext = os.path.splitext(filename)
    unc_file_from = os.path.join(temp_dir, unc_filename)
    file_from = os.path.join(temp_dir, filename)
    file_to = os.path.join(path, filename)
    if os.path.exists(file_to):
        os.remove(file_to)
    print("Storing " + file_to)
    ret = sh.bzip2(unc_file_from).exit_code
    if ret == 0:
        ret = sh.mv(file_from, file_to).exit_code
    return ret == 0

def extract_rsync_tarball(path, time, target_dir, temp_dir, template,
                          rsync_exempt):
    build_dir = os.path.join(temp_dir, "portage_update_build")
    force_directories(build_dir, purge=True)
    filename = os.path.join(path, template % time)

    print("Extract tarball " + filename)
    sh.tar("-xvp", file=filename, directory=build_dir)

    print("Rsync to " + target_dir)
    exempteds = ('--exclude="%s"' % x for x in rsync_exempt)
    sh.rsync(os.path.join(build_dir, "portage", ""), os.path.join(target_dir, ""),
             "-av", "--delete", " ".join(exempteds))
    sh.rm("-r", build_dir)
