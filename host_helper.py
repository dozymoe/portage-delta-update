import os
from requests import get as http_get
try:
    from bs4 import BeautifulSoup as bs
except ImportError:
    from BeautifulSoup import BeautifulSoup as bs

from local_helper import *


class PatchApplyException(Exception):
    pass


class PatchDownloadException(Exception):
    pass


def apply_patch(config, time_f, time_t):
    template = config['local']['template']
    file_f = os.path.join(config['path']['archives'], template % time_f)
    file_t = os.path.join(config['path']['temp'], template % time_t)

    patch = os.path.join(config['path']['temp'],
            config['host']['delta']['template'] % (time_f, time_t))

    if os.system('patcher %s %s %s' % (file_f, patch, file_t)) != 0:
        raise PatchApplyException('failed to patch')

    os.remove(file_f)
    os.remove(patch)
    os.rename(file_t, os.path.join(config['path']['archives'],
            template % time_t))


def download_patch(config, time_f, time_t):
    filename = config['host']['delta']['template'] % (time_f, time_t)
    filepath = os.path.join(config['path']['temp'], filename)
    url = config['host']['delta']['url']

    # download compressed patch
    response = http_get(os.path.join(url, filename), stream=True)

    with open(filepath, 'wb') as f:
        for chunk in response.iter_content(65536):
            f.write(chunk)

    # check md5
    response = http_get(os.path.join(url, filename + '.md5sum')).text
    md5sum = response[:response.index(' ')]

    if md5sum != file_md5(filepath):
        raise PatchDownloadException('invalid hash')


def get_deltas(config, time_c):
    response = http_get(config['host']['delta']['url'])
    soup = bs(response.text, 'html.parser')

    for l in soup.findAll('a'):
        match = config['host']['delta']['regex'].search(l.text)
        if not match:
            continue
        time_f = int(match.group('time_f'))

        # accept if `from time` is equal or later than ours
        if time_f >= time_c:
            yield (time_f, int(match.group('time_t')))
