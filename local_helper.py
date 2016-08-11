import os
from hashlib import md5

def file_md5(filename):
    hasher = md5()
    with open(filename, 'rb') as f:
        buf = f.read(65536)
        while len(buf) > 0:
            hasher.update(buf)
            buf = f.read(65536)
    return hasher.hexdigest()


def clean_target(config):
    exclude = list(config['target']['exclude'])[:]
    exclude.append('metadata')

    for dir_ in os.listdir(config['path']['target']):
        if dir_ in exclude:
            continue
        tdir = os.path.join(config['path']['target'], dir_)
        if os.path.isdir(tdir):
            os.system('rm -r %s' % tdir)
        else:
            os.remove(tdir)

    os.system('rm -r %s' % os.path.join(config['path']['target'],
            'metadata'))


def untar_tarball(config, time):
    filepath = os.path.join(config['path']['archives'],
            config['local']['template'] % time)
    target = os.path.dirname(os.path.realpath(config['path']['target']))
    return os.system('tar -xvpf %s -C %s' % (
            filepath, target))


def mount_tarball(config, time):
    target = config['path']['tarmount']
    if not os.path.exists(target):
        os.makedirs(target)

    filepath = os.path.join(config['path']['archives'],
            config['local']['template'] % time)
    archivemount_options = [
        '-o nobackup',
        '-o readonly',
    ]
    return os.system('archivemount %s %s %s' % (
            ' '.join(archivemount_options), filepath,
            target)) == 0


def rsync_tarball(config):
    no_metadata = list(config['rsync']['exclude'])[:]
    no_metadata.append('/metadata/***')
    excludes = ('--exclude="%s"' % x for x in no_metadata)
    source = os.path.join(config['path']['tarmount'], 'portage', '')
    target = os.path.join(config['path']['target'], '')

    if os.system('rsync -a --delete %s %s %s' % (' '.join(excludes),
            source, target)) == 0:

        source = os.path.join(source, 'metadata', '')
        target = os.path.join(target, 'metadata', '')
        return os.system('rsync -a --delete %s %s' % (source,
                target)) == 0

    return False


def timestamp_from_downloaded_tars(config):
    time = 0
    for f in os.listdir(config['path']['archives']):
        match = config['local']['regex'].search(f)
        if not match:
            continue
        time_l = int(match.group('time'))

        if time_l < time:
            # auto remove older tar balls
            os.remove(os.path.join(path,
                    config['local']['template'] % time_l))
        elif time_l > time:
            # auto remove older tar balls
            if time > 0:
                os.remove(os.path.join(path,
                        config['local']['template'] % time))
            # accept newer tar balls
            time = time_l
    return time


def umount_tarball(config):
    return os.system('umount %s' % config['path']['tarmount']) == 0
