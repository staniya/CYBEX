#!/usr/bin/env python
from pprint import pprint
import re
from collections import Counter
import jsondate
import json
import logging
from argparse import ArgumentParser
from datetime import datetime, timedelta
import html
import time
from traceback import format_exc
from itertools import chain
from functools import partial

from telegram import ParseMode, Bot
from telegram.ext import Updater, CommandHandler, MessageHandler, Filters, RegexHandler
from telegram.error import TelegramError
from telegram.ext.dispatcher import run_async

from model import load_group_config
from util import find_username_links, find_external_links, fetch_user_type
from database import connect_db

SUPERUSER_IDS = {46284539}
# List of keys allowed to use in set_setting/get_setting
GROUP_SETTING_KEYS = ('publog', 'log_channel_id', 'logformat', 'safe_hours')
# Channel of global channel to translate ALL spam
GLOBAL_LOG_CHANNEL_ID = {
    'production': -1001148916224,
    'test': -1001318592769,
}
# Default time to reject link and forwarded posts from new user
DEFAULT_SAFE_HOURS = 24
db = connect_db()

# Some shitty global code
JOINED_USERS = {}
GROUP_CONFIG = load_group_config(db)
DELETE_EVENTS = {}


@run_async
def handle_stat(bot, update):
    msg = update.effective_message
    if msg.chat.type != 'private':
        return
    cnt = {
        'delete_msg': [],
        'chat': [],
    }
    today = datetime.utcnow().replace(hour=0, minute=0, second=0, microsecond=0)
    for x in range(7):
        day = today - timedelta(days=x)
        stat = db.day_stat.find_one({'date': day})
        if stat:
            cnt['delete_msg'].insert(0, stat['delete_msg'])
            cnt['chat'].insert(0, stat['chat'])
        else:
            cnt['delete_msg'].insert(0, 'NA')
            cnt['chat'].insert(0, 'NA')

    ret = '*Recent 7 days stat*\n'
    ret += '\n'
    ret += 'Deleted messages:\n'
    ret += ('    %s' % '|'.join(map(str, cnt['delete_msg']))) + '\n'
    ret += 'Affected chats:\n'
    ret += ('    %s' % '|'.join(map(str, cnt['chat']))) + '\n'
    bot.send_message(msg.chat.id, ret, parse_mode=ParseMode.MARKDOWN)


def register_handlers(dispatcher, mode):

    dispatcher.add_handler(CommandHandler('stat', handle_stat))
    dispatcher.add_handler(RegexHandler(
        r'^/setlogformat ', handle_setlogformat, channel_post_updates=True
    ))
    dispatcher.add_handler(MessageHandler(
        Filters.all, partial(handle_any_message, mode), edited_updates=True
    ))