import re
from urllib.parse import quote
try:
    from urllib.request import urlopen
except ImportError as e:
    print(str(e))
import logging

RE_USERNAME = re.compile(r'@[a-z][_a-z0-9]{4,30}', re.I)


def find_username_links(text):
    return RE_USERNAME.findall(text)


def fetch_user_type(username):
    url = 'https://t.me/{}'.format(quote(username))
    try:
        data = urlopen(url, timeout=2).read().decode('utf-8')
    except OSError:
        logging.exception('Failed to fetch URL: {}'.format(url))
        return None
    else:
        if '>View Group<' in data:
            return 'group'
        elif '>Send Message<' in data:
            return 'user'
        elif '>View Channel<' in data:
            return 'channel'
        else:
            logging.error('Could not detect user type: {}'.format(url))