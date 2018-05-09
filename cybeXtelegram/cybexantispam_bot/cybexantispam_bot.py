#!/usr/bin/env python
import html
import logging
import os
import re
import sys
from argparse import ArgumentParser
from datetime import datetime, timedelta
from functools import partial
from pathlib import Path
from pprint import pprint
from traceback import format_exc

import jsondate
import yaml
from telegram import ParseMode, Bot
from telegram.ext import Updater, CommandHandler, MessageHandler, Filters, RegexHandler
from telegram.ext.dispatcher import run_async

# from util import find_username_links, find_external_links, fetch_user_type
from database import connect_db
from model import load_group_config
from util import fetch_user_type

HELP = """
*CYBEX Anti-Spam Bot Help*

*cybexantispam_bot deletes all posts by users that joined less than a month ago that contain:*
1. links
2. images
3. videos
4. stickers
5. documents
6. locations
7. audio
7. voice recordings

*Usage*
1. Add [@cybexantispam_bot](https://t.me/cybexantispam_bot) to your group.
2. Go to group settings / users list / promote user to admin
3. Enable only one item: Delete messages
4. Click SAVE button
5. Enjoy!

*Commands*
/help - display this help message
/stat - display simple statistics about number of deleted messages
/cybexantispamset publog=[yes|no] - enable/disable messages to group about deleted posts
/cybexantispamset safehours=[int] - number in hours, how long new users are restricted to post links and forward posts, default is 24 hours (Allowed value is number between 1 and 8760)
/cybexantispamget publog - get value of publog setting
/cybexantispamget safehours - get value of safehours setting

*How to log deleted messages to private channel*
Add bot to the channel as admin. Write /setlog to the channel. Forward message to the group.
Write /unsetlog in the group to disable logging to channel.
You can control format of logs with /setlogformat <format> command sent to the channel. The argument of this command could be: simple, json, forward or any combination of items delimited by space e.g. json,forward:
simple - display basic info about message + the
text of message (or caption text of photo/video)
json - display full message data in JSON format
forward - simply forward message to the channel (just message, no data about chat or author).

*Questions, Feedback*
Support chat - [@Administrators](https://t.me/joinchat/IJzAyRFXj_C42lkLd8iVWQ)
Author's telegram -  [@Shinno](https://t.me/Shinno1002)
Use github issues to report bugs - [github issues](https://github.com/staniya/CYBEX/issues)
"""

'''
# Load the config file
# Set the Botname / Token
'''


def save_message_event(db, event_type, msg, **kwargs):
    event = msg.to_dict()
    event.update({
        'date': datetime.utcnow(),
        'type': event_type,
    })
    event.update(**kwargs)
    db.event.save(event)


def register_handlers(dispatcher, mode):
    assert mode in ('production', 'test')
    dispatcher.add_handler(RegexHandler(
        r'^/setlogformat ', handle_setlogformat, channel_post_updates=True
    ))
    dispatcher.add_handler(MessageHandler(
        Filters.all, partial(handle_any_message, mode), edited_updates=True
    ))


def main():
    parser = ArgumentParser()
    parser.add_argument('--mode', default='production')
    opts = parser.parse_args()
    logging.basicConfig(level=logging.DEBUG)
    updater = init_updater_with_mode(opts.mode)
    dispatcher = updater.dispatcher
    register_handlers(dispatcher, opts.mode)
    updater.bot.delete_webhook()
    updater.start_polling()
