# -*- coding: utf-8 -*-
__author__ = 'ShinnosukeTaniya'

import memcache

from . import models
import json


with open('config.json', 'r') as file:
    CONFIG = json.loads(file.read())

cache = memcache.Client(CONFIG['cache']['servers'], debug=CONFIG['cache']['debug'])
