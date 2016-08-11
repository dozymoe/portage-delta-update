import os
from datetime import datetime, timedelta

def timestamp_from_portage(config):
    path = config['path']['target']
    filename = os.path.join(path, 'metadata', 'timestamp.x')
    if os.path.exists(filename):
        with open(filename, 'r') as f:
            time_str = f.readline()
            time_str = time_str[:time_str.index(' ')]
            time = datetime.utcfromtimestamp(int(time_str))
            time -= timedelta(days=1)
            return int(time.strftime('%Y%m%d'))
    return 0
