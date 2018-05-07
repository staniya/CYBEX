import re
try:
    from urllib.request import urlopen
except ImportError as e:
    print(str(e))

RE_USERNAME = re.compile(r'@[a-z][_a-z0-9]{4,30}', re.I)


def find_username_links(text):
    return RE_USERNAME.findall(text)
