import os
import re
from collections import Counter
from pprint import pprint
from pathlib import Path
from traceback import format_exc
import urllib
# TODO make this compatible for python3
from daemonize import Daemonize

import jsondate
import yaml
import html
import sys
import logging
from argparse import ArgumentParser
import telebot
from datetime import datetime, timedelta
import time

from database import connect_db
from model import load_group_config

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
3. Enable: Delete messages
4. Click SAVE button

*Commands*
/help - display this help message
/stat - display simple statistics about number of deleted messages
/cybexantispamrealbotset publog=[yes|no] - enable/disable messages to group about deleted posts
/cybexantispamrealbotset safehours=[int] - number in hours, how long new users are restricted to post links and forward posts, default is 24 hours (Allowed value is number between 1 and 8760)
/cybexantispamget publog - get value of publog setting
/cybexantispamget safehours - get value of safehours setting

*How to log deleted messages to private channel*
Add bot to the channel as admin. Write /setlog to the channel. Forward message to the group.
Write /unsetlog in the group to disable logging to channel.
You can control format of logs with /setlogformat <format> command sent to the channel. The argument of this command could be: simple, json, forward or any combination of items delimited by space e.g. json,forward:
simple - display basic info about message + the
text of message (or caption text of photo/video)
json - display full message data in JSON format

*Questions, Feedback*
Support chat - [@Administrators](https://t.me/joinchat/IJzAyRFXj_C42lkLd8iVWQ)
Author's telegram -  [@Shinno](https://t.me/Shinno1002)
Use github issues to report bugs - [github issues](https://github.com/staniya/CYBEX/issues)
"""

# turn application into a daemon
pid = "/tmp/cybex.pid"

'''
# Load the config file
# Set the Botname / Token
'''
PATH = os.path.dirname(os.path.abspath(__file__))
config_file = PATH + '/var/config.yaml'
my_file = Path(config_file)
if my_file.is_file():
    with open(config_file) as fp:
        config = yaml.load(fp)
else:
    pprint('config.yaml file does not exist')
    sys.exit()

# # production
BOTNAME = config['BOT_USERNAME']
TELEGRAM_BOT_TOKEN = config['BOT_TOKEN']

# test
BOTNAME_TEST = config['BOT_USERNAME1']
TELEGRAM_BOT_TOKEN_TEST = config['BOT_TOKEN1']

SUPERUSER_IDS = {
    547143881,
    588855253,
    521939957,
    566494759,
    483171166,
}
# List of keys allowed to use in set_setting/get_setting
GROUP_SETTING_KEYS = ('publog', 'log_channel_id', 'logformat', 'safehours')
# Channel of global channel to translate ALL spam
GLOBAL_LOG_CHANNEL_ID = {
    'production': -1001313978621,
}
# Default time to reject link and forwarded posts from new user
DEFAULT_SAFE_HOURS = 720
db = connect_db()

# Some shitty global code
JOINED_USERS = {}
GROUP_CONFIG = load_group_config(db)
DELETE_EVENTS = {}


def create_bot(api_token, db):
    bot = telebot.TeleBot(api_token)

    @bot.message_handler(content_types=['sticker'])
    def handle_sticker(msg):
        if (
                msg.from_user.username == 'Shinno'
                and (msg.text == 'del' or msg.caption == 'del')
        ):
            return _run_main(msg, True, 'debug delete')
        join_date = get_join_date(msg.chat.id, msg.from_user.id)
        if join_date is None:
            logging.error("No join_date")
            return _run_main(msg, False, None)
        safehours = get_setting(
            GROUP_CONFIG, msg.chat.id, 'safehours', DEFAULT_SAFE_HOURS
        )
        if datetime.utcnow() - timedelta(hours=safehours) > join_date:
            logging.error("User has been in the chat longer than the set safe hours")
            return _run_main(msg, False, None)
        else:
            # try:
            #     # TODO if you want to delete stickers, enable message below
            #     # bot.delete_message(msg.chat.id, msg.message_id)
            #     db.event.save({
            #         'type': 'delete_sticker',
            #         'chat_id': msg.chat.id,
            #         'chat_username': msg.chat.username,
            #         'user_id': msg.from_user.id,
            #         'username': msg.from_user.username,
            #         'date': datetime.utcnow(),
            #     })
            return _run_main(msg, False, 'sticker')

    @bot.message_handler(content_types=['document'])
    def handle_document(msg):
        if (
                msg.from_user.username == 'Shinno'
                and (msg.text == 'del' or msg.caption == 'del')
        ):
            return _run_main(msg, True, 'debug delete')
        join_date = get_join_date(msg.chat.id, msg.from_user.id)
        if join_date is None:
            logging.error("No join_date")
            return _run_main(msg, False, None)
        safehours = get_setting(
            GROUP_CONFIG, msg.chat.id, 'safehours', DEFAULT_SAFE_HOURS
        )
        if datetime.utcnow() - timedelta(hours=safehours) > join_date:
            logging.error("User has been in the chat longer than the set safe hours")
            return _run_main(msg, False, None)
        else:
            try:
                if msg.from_user.id not in SUPERUSER_IDS:
                    bot.delete_message(msg.chat.id, msg.message_id)
                    db.event.save({
                        'type': 'delete_document',
                        'chat_id': msg.chat.id,
                        'chat_username': msg.chat.username,
                        'user_id': msg.from_user.id,
                        'username': msg.from_user.username,
                        'date': datetime.utcnow(),
                        # 'document': {
                        #     'file_id': msg.document.file_id,
                        #     'file_name': msg.document.file_name,
                        #     'mime_type': msg.document.mime_type,
                        #     'file_size': msg.document.file_size,
                        #     'thumb': msg.document.thumb.__dict__ if msg.document.thumb else None,
                        # },
                    })
                    return _run_main(msg, True, 'document')
                else:
                    return _run_main(msg, False, 'admin')
            except Exception or AttributeError as ex:
                db.fail.save({
                    'date': datetime.utcnow(),
                    'reason': str(ex),
                    'traceback': format_exc(),
                    'chat_id': msg.chat.id,
                    'msg_id': msg.message_id,
                })
                if (
                        'message to delete not found' in str(ex)
                        # or "message can\'t be deleted" in str(ex)
                        or "be deleted" in str(ex)
                        or 'MESSAGE_ID_INVALID' in str(ex)
                        # or 'message to forward not found' in str(ex)
                ):
                    logging.error('Failed to process spam message: {}'.format(
                        ex))
                else:
                    raise

    @bot.message_handler(content_types=['photo'])
    def handle_photo(msg):
        if (
                msg.from_user.username == 'Shinno'
                and (msg.text == 'del' or msg.caption == 'del')
        ):
            return _run_main(msg, True, 'debug delete')
        join_date = get_join_date(msg.chat.id, msg.from_user.id)
        if join_date is None:
            logging.error("No join_date")
            return _run_main(msg, False, None)
        safehours = get_setting(
            GROUP_CONFIG, msg.chat.id, 'safehours', DEFAULT_SAFE_HOURS
        )
        if datetime.utcnow() - timedelta(hours=safehours) > join_date:
            logging.error("User has been in the chat longer than the set safe hours")
            return _run_main(msg, False, None)
        else:
            try:
                if msg.from_user.id not in SUPERUSER_IDS:
                    bot.delete_message(msg.chat.id, msg.message_id)
                    db.event.save({
                        'type': 'delete_photo',
                        'chat_id': msg.chat.id,
                        'chat_username': msg.chat.username,
                        'user_id': msg.from_user.id,
                        'username': msg.from_user.username,
                        'date': datetime.utcnow(),
                        # 'photo': {
                        #     'photo': 'photo_deleted',
                        #     # TODO how to get the file_id for this one?
                        # },
                    })
                    return _run_main(msg, True, 'photo')
                else:
                    return _run_main(msg, False, 'admin')
            except Exception or AttributeError as ex:
                db.fail.save({
                    'date': datetime.utcnow(),
                    'reason': str(ex),
                    'traceback': format_exc(),
                    'chat_id': msg.chat.id,
                    'msg_id': msg.message_id,
                })
                if (
                        'message to delete not found' in str(ex)
                        # or "message can\'t be deleted" in str(ex)
                        or "be deleted" in str(ex)
                        or 'MESSAGE_ID_INVALID' in str(ex)
                        # or 'message to forward not found' in str(ex)
                ):
                    logging.error('Failed to process spam message: {}'.format(
                        ex))
                else:
                    raise

    @bot.message_handler(content_types=['audio'])
    def handle_audio(msg):
        if (
                msg.from_user.username == 'Shinno'
                and (msg.text == 'del' or msg.caption == 'del')
        ):
            return _run_main(msg, True, 'debug delete')
        join_date = get_join_date(msg.chat.id, msg.from_user.id)
        if join_date is None:
            logging.error("No join_date")
            return _run_main(msg, False, None)
        safehours = get_setting(
            GROUP_CONFIG, msg.chat.id, 'safehours', DEFAULT_SAFE_HOURS
        )
        if datetime.utcnow() - timedelta(hours=safehours) > join_date:
            logging.error("User has been in the chat longer than the set safe hours")
            return _run_main(msg, False, None)
        else:
            try:
                if msg.from_user.id not in SUPERUSER_IDS:
                    bot.delete_message(msg.chat.id, msg.message_id)
                    db.event.save({
                        'type': 'delete_audio',
                        'chat_id': msg.chat.id,
                        'chat_username': msg.chat.username,
                        'user_id': msg.from_user.id,
                        'username': msg.from_user.username,
                        'date': datetime.utcnow(),
                        # 'audio': {
                        #     'file_id': msg.audio.file_id,
                        #     'title': msg.audio.title,
                        #     'file_size': msg.audio.file_size,
                        #     'performer': msg.audio.performer,
                        #     'mime_type': msg.audio.mime_type,
                        # },
                    })
                    return _run_main(msg, True, 'audio')
                else:
                    return _run_main(msg, False, 'admin')
            except Exception or AttributeError as ex:
                db.fail.save({
                    'date': datetime.utcnow(),
                    'reason': str(ex),
                    'traceback': format_exc(),
                    'chat_id': msg.chat.id,
                    'msg_id': msg.message_id,
                })
                if (
                        'message to delete not found' in str(ex)
                        # or "message can\'t be deleted" in str(ex)
                        or "be deleted" in str(ex)
                        or 'MESSAGE_ID_INVALID' in str(ex)
                        # or 'message to forward not found' in str(ex)
                ):
                    logging.error('Failed to process spam message: {}'.format(
                        ex))
                else:
                    raise

    @bot.message_handler(content_types=['voice'])
    def handle_voice(msg):
        if (
                msg.from_user.username == 'Shinno'
                and (msg.text == 'del' or msg.caption == 'del')
        ):
            return _run_main(msg, True, 'debug delete')
        join_date = get_join_date(msg.chat.id, msg.from_user.id)
        if join_date is None:
            logging.error("No join_date")
            return _run_main(msg, False, None)
        safehours = get_setting(
            GROUP_CONFIG, msg.chat.id, 'safehours', DEFAULT_SAFE_HOURS
        )
        if datetime.utcnow() - timedelta(hours=safehours) > join_date:
            logging.error("User has been in the chat longer than the set safe hours")
            return _run_main(msg, False, None)
        else:
            try:
                if msg.from_user.id not in SUPERUSER_IDS:
                    bot.delete_message(msg.chat.id, msg.message_id)
                    db.event.save({
                        'type': 'delete_voice',
                        'chat_id': msg.chat.id,
                        'chat_username': msg.chat.username,
                        'user_id': msg.from_user.id,
                        'username': msg.from_user.username,
                        'date': datetime.utcnow(),
                        # 'voice': {
                        #     'file_id': msg.voice.file_id,
                        #     'file_size': msg.voice.file_size,
                        #     'mime_type': msg.voice.mime_type,
                        # },
                    })
                    return _run_main(msg, True, 'voice')
                else:
                    return _run_main(msg, False, 'admin')
            except Exception or AttributeError as ex:
                db.fail.save({
                    'date': datetime.utcnow(),
                    'reason': str(ex),
                    'traceback': format_exc(),
                    'chat_id': msg.chat.id,
                    'msg_id': msg.message_id,
                })
                if (
                        'message to delete not found' in str(ex)
                        # or "message can\'t be deleted" in str(ex)
                        or "be deleted" in str(ex)
                        or 'MESSAGE_ID_INVALID' in str(ex)
                        # or 'message to forward not found' in str(ex)
                ):
                    logging.error('Failed to process spam message: {}'.format(
                        ex))
                else:
                    raise

    @bot.message_handler(content_types=['video'])
    def handle_video(msg):
        if (
                msg.from_user.username == 'Shinno'
                and (msg.text == 'del' or msg.caption == 'del')
        ):
            return _run_main(msg, True, 'debug delete')
        join_date = get_join_date(msg.chat.id, msg.from_user.id)
        if join_date is None:
            logging.error("No join_date")
            return _run_main(msg, False, None)
        safehours = get_setting(
            GROUP_CONFIG, msg.chat.id, 'safehours', DEFAULT_SAFE_HOURS
        )
        if datetime.utcnow() - timedelta(hours=safehours) > join_date:
            logging.error("User has been in the chat longer than the set safe hours")
            return _run_main(msg, False, None)
        else:
            try:
                if msg.from_user.id not in SUPERUSER_IDS:
                    bot.delete_message(msg.chat.id, msg.message_id)
                    db.event.save({
                        'type': 'delete_video',
                        'chat_id': msg.chat.id,
                        'chat_username': msg.chat.username,
                        'user_id': msg.from_user.id,
                        'username': msg.from_user.username,
                        'date': datetime.utcnow(),
                        # 'video': {
                        #     'file_id': msg.video.file_id,
                        #     'file_size': msg.video.file_size,
                        #     'mime_type': msg.video.mime_type,
                        # },
                    })
                    return _run_main(msg, True, 'video')
                else:
                    return _run_main(msg, False, 'admin')
            except Exception or AttributeError as ex:
                db.fail.save({
                    'date': datetime.utcnow(),
                    'reason': str(ex),
                    'traceback': format_exc(),
                    'chat_id': msg.chat.id,
                    'msg_id': msg.message_id,
                })
                if (
                        'message to delete not found' in str(ex)
                        # or "message can\'t be deleted" in str(ex)
                        or "be deleted" in str(ex)
                        or 'MESSAGE_ID_INVALID' in str(ex)
                        # or 'message to forward not found' in str(ex)
                ):
                    logging.error('Failed to process spam message: {}'.format(
                        ex))
                else:
                    raise

    @bot.message_handler(content_types=['location'])
    def handle_location(msg):
        if (
                msg.from_user.username == 'Shinno'
                and (msg.text == 'del' or msg.caption == 'del')
        ):
            return _run_main(msg, True, 'debug delete')
        join_date = get_join_date(msg.chat.id, msg.from_user.id)
        if join_date is None:
            logging.error("No join_date")
            return _run_main(msg, False, None)
        safehours = get_setting(
            GROUP_CONFIG, msg.chat.id, 'safehours', DEFAULT_SAFE_HOURS
        )
        if datetime.utcnow() - timedelta(hours=safehours) > join_date:
            logging.error("User has been in the chat longer than the set safe hours")
            return _run_main(msg, False, None)
        else:
            try:
                if msg.from_user.id not in SUPERUSER_IDS:
                    bot.delete_message(msg.chat.id, msg.message_id)
                    db.event.save({
                        'type': 'delete_location',
                        'chat_id': msg.chat.id,
                        'chat_username': msg.chat.username,
                        'user_id': msg.from_user.id,
                        'username': msg.from_user.username,
                        'date': datetime.utcnow(),
                        # 'location': {
                        #     'latitude': msg.location.latitude,
                        #     'longitude': msg.location.longitude,
                        # },
                    })
                    return _run_main(msg, True, 'location')
                else:
                    return _run_main(msg, False, 'admin')
            except Exception or AttributeError as ex:
                db.fail.save({
                    'date': datetime.utcnow(),
                    'reason': str(ex),
                    'traceback': format_exc(),
                    'chat_id': msg.chat.id,
                    'msg_id': msg.message_id,
                })
                if (
                        'message to delete not found' in str(ex)
                        # or "message can\'t be deleted" in str(ex)
                        or "be deleted" in str(ex)
                        or 'MESSAGE_ID_INVALID' in str(ex)
                        # or 'message to forward not found' in str(ex)
                ):
                    logging.error('Failed to process spam message: {}'.format(
                        ex))
                else:
                    raise

    @bot.message_handler(content_types=['contact'])
    def handle_contact(msg):
        if (
                msg.from_user.username == 'Shinno'
                and (msg.text == 'del' or msg.caption == 'del')
        ):
            return _run_main(msg, True, 'debug delete')
        join_date = get_join_date(msg.chat.id, msg.from_user.id)
        if join_date is None:
            logging.error("No join_date")
            return _run_main(msg, False, None)
        safehours = get_setting(
            GROUP_CONFIG, msg.chat.id, 'safehours', DEFAULT_SAFE_HOURS
        )
        if datetime.utcnow() - timedelta(hours=safehours) > join_date:
            logging.error("User has been in the chat longer than the set safe hours")
            return _run_main(msg, False, None)
        else:
            try:
                if msg.from_user.id not in SUPERUSER_IDS:
                    bot.delete_message(msg.chat.id, msg.message_id)
                    db.event.save({
                        'type': 'delete_contact',
                        'chat_id': msg.chat.id,
                        'chat_username': msg.chat.username,
                        'user_id': msg.from_user.id,
                        'username': msg.from_user.username,
                        'date': datetime.utcnow(),
                        # 'contact': {
                        #     'phone_number': msg.contact.phone_number,
                        #     'first_name': msg.contact.first_name,
                        # },
                    })
                    return _run_main(msg, True, 'contact')
                else:
                    return _run_main(msg, False, 'admin')
            except Exception or AttributeError as ex:
                db.fail.save({
                    'date': datetime.utcnow(),
                    'reason': str(ex),
                    'traceback': format_exc(),
                    'chat_id': msg.chat.id,
                    'msg_id': msg.message_id,
                })
                if (
                        'message to delete not found' in str(ex)
                        # or "message can\'t be deleted" in str(ex)
                        or "be deleted" in str(ex)
                        or 'MESSAGE_ID_INVALID' in str(ex)
                        # or 'message to forward not found' in str(ex)
                ):
                    logging.error('Failed to process spam message: {}'.format(
                        ex))
                else:
                    raise

    @bot.message_handler(content_types=['video_note'])
    def handle_video_note(msg):
        if (
                msg.from_user.username == 'Shinno'
                and (msg.text == 'del' or msg.caption == 'del')
        ):
            return _run_main(msg, True, 'debug delete')
        join_date = get_join_date(msg.chat.id, msg.from_user.id)
        if join_date is None:
            logging.error("No join_date")
            return _run_main(msg, False, None)
        safehours = get_setting(
            GROUP_CONFIG, msg.chat.id, 'safehours', DEFAULT_SAFE_HOURS
        )
        if datetime.utcnow() - timedelta(hours=safehours) > join_date:
            logging.error("User has been in the chat longer than the set safe hours")
            return _run_main(msg, False, None)
        else:
            try:
                if msg.from_user.id not in SUPERUSER_IDS:
                    bot.delete_message(msg.chat.id, msg.message_id)
                    db.event.save({
                        'type': 'delete_video_note',
                        'chat_id': msg.chat.id,
                        'chat_username': msg.chat.username,
                        'user_id': msg.from_user.id,
                        'username': msg.from_user.username,
                        'date': datetime.utcnow(),
                        # 'video_note': {
                        #     'videonote': 'video note deleted',
                        #     # TODO get file_id for this one
                        # },
                    })
                    return _run_main(msg, True, 'video_note')
                else:
                    return _run_main(msg, False, 'admin')
            except Exception or AttributeError as ex:
                db.fail.save({
                    'date': datetime.utcnow(),
                    'reason': str(ex),
                    'traceback': format_exc(),
                    'chat_id': msg.chat.id,
                    'msg_id': msg.message_id,
                })
                if (
                        'message to delete not found' in str(ex)
                        # or "message can\'t be deleted" in str(ex)
                        or "be deleted" in str(ex)
                        or 'MESSAGE_ID_INVALID' in str(ex)
                        # or 'message to forward not found' in str(ex)
                ):
                    logging.error('Failed to process spam message: {}'.format(
                        ex))
                else:
                    raise

    @bot.message_handler(commands=['start', 'help'])
    def handle_start_help(msg):
        if msg.chat.type == 'private':
            bot.reply_to(msg, HELP, parse_mode='Markdown')
        else:
            if msg.text.strip() in (
                    '/start', '/start@cybexantispamrealbot', '/start@cybexantispamrealtestbot',
                    '/help', '/help@cybexantispamrealbot', '/help@cybexantispamrealtestbot'
            ):
                try:
                    bot.delete_message(msg.chat.id, msg.message_id)
                except Exception as ex:
                    if (
                            'message to delete not found' in str(ex)
                            # or "message can\'t be deleted" in str(ex)
                            or "be deleted" in str(ex)
                            or "MESSAGE_ID_INVALID" in str(ex)
                    ):
                        logging.error('Failed to delete command message {}'.format(ex))
                    else:
                        raise

    def get_join_date(chat_id, user_id):
        key = (chat_id, user_id)
        if key in JOINED_USERS:
            return JOINED_USERS[key]
        else:
            item = db.joined_user.find_one(
                {'chat_id': chat_id, 'user_id': user_id},
                {'date': 1, '_id': 0}
            )
            if item:
                JOINED_USERS[key] = item['date']
                return JOINED_USERS[key]
            else:
                return None

    def set_setting(group_config, group_id, key, val):
        assert key in GROUP_SETTING_KEYS
        db.config.find_one_and_update(
            {
                'group_id': group_id,
                'key': key,
            },
            {'$set': {'value': val}},
            upsert=True,
        )
        group_config[(group_id, key)] = val

    def get_setting(group_config, group_id, key, default=None):
        assert key in GROUP_SETTING_KEYS
        try:
            return group_config[(group_id, key)]
        except KeyError:
            return default

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

    def process_user_type(username):
        username = username.lower()
        logging.debug('Querying {} type from db'.format(username))
        user = db.user.find_one({'username': username})
        if user:
            logging.debug('Record found, type is: {}'.format(user['type']))
            return user['type']
        else:
            logging.debug('Doing network request for type of {}'.format(username))
            user_type = fetch_user_type(username)
            logging.debug('Result is: {}'.format(user_type))
            if user_type:
                db.user.find_one_and_update(
                    {'username': username},
                    {'$set': {
                        'username': username,
                        'type': user_type,
                        'added': datetime.utcnow(),
                    }},
                    upsert=True
                )
            return user_type

    def get_delete_link(msg):
        if (
                msg.from_user.username == 'Shinno'
                and (msg.text == 'del' or msg.caption == 'del')
        ):
            return True, 'debug delete'
        join_date = get_join_date(msg.chat.id, msg.from_user.id)
        if join_date is None:
            return False, None
        safehours = get_setting(
            GROUP_CONFIG, msg.chat.id, 'safehours', DEFAULT_SAFE_HOURS
        )
        if datetime.utcnow() - timedelta(hours=safehours) > join_date:
            return False, None
        locations = [
            ('text', msg.entities or []),
            ('caption', msg.caption_entities or []),
        ]
        for scope, entities in locations:
            for ent in entities:
                # TODO maybe need to change all of this to True later
                if ent.type in ('url', 'text_link'):
                    db.event.save({
                        'type': 'delete_link',
                        'chat_id': msg.chat.id,
                        'chat_username': msg.chat.username,
                        'user_id': msg.from_user.id,
                        'username': msg.from_user.username,
                        'date': datetime.utcnow(),
                    })
                    return True, 'external link'
                if ent.type in ('email',):
                    db.event.save({
                        'type': 'delete_link',
                        'chat_id': msg.chat.id,
                        'chat_username': msg.chat.username,
                        'user_id': msg.from_user.id,
                        'username': msg.from_user.username,
                        'date': datetime.utcnow(),
                    })
                    return True, 'email'
                if ent.type == 'mention':
                    text = msg.text if scope == 'text' else msg.caption
                    username = text[ent.offset:ent.offset + ent.length].lstrip('@')
                    user_type = process_user_type(username)
                    if user_type in ('group', 'channel'):
                        return False, '@-link to group/channel'
            if msg.forward_from or msg.forward_from_chat:
                return False, 'forwarded'
            return False, None

    @bot.message_handler(commands=['setlogformat'])
    # TODO you may have to make this a regex handler
    def handle_setlogformat(msg):
        if msg.chat.type != 'channel':
            admin_ids = [x.user.id for x in bot.get_chat_administrators(msg.chat.id)]
            if msg.from_user.id not in admin_ids:
                # Silently ignore /setlogformat command from non-admin in non-channel
                delete_message_safe(msg)
            else:
                bot.send_message(msg.chat.id, 'This command has to be called from a channel')
            return
        valid_formats = ('json', 'simple')
        formats = msg.text.split(' ')[-1].split(',')
        if any(x not in valid_formats for x in formats):
            bot.send_message(msg.chat.id, 'Invalid arguments. Valid choices: {}'.format(
                ', '.join(valid_formats), ))
            return
        set_setting(GROUP_CONFIG, msg.chat.id, 'logformat', formats)
        bot.send_message(msg.chat.id, 'Set logformat for this channel')

    @bot.message_handler(commands=['setlog'])
    def handle_setlog(msg):
        admin_ids = [x.user.id for x in bot.get_chat_administrators(msg.chat.id)]
        if msg.chat.type not in ('group', 'supergroup'):
            bot.send_message(msg.chat.id, "This command has to be called from a group or a supergroup")
            return
        if not msg.forward_from_chat or msg.forward_from_chat.type != 'channel':
            if msg.from_user.id not in admin_ids:
                # Silently ignore /setlog command from non-admin
                delete_message_safe(msg)
                pass
            else:
                bot.send_message(msg.chat.id, 'Command /setlog must be forwarded from channel')
                return
            channel = msg.forward_from_chat
            if bot.get_me().id not in admin_ids:
                bot.send_message(msg.chat.id, 'Assign me as an administrator in the chat')
                return

            if msg.from_user.id not in admin_ids:
                delete_message_safe(msg)
                bot.send_message(msg.chat.id, "You are not an administrator")
                return

            set_setting(GROUP_CONFIG, msg.chat.id, 'log_channel_id', channel.id)
            tgid = '@{}'.format(msg.chat.username if msg.chat.username else '#{}'.format(msg.chat.id))
            bot.send_message(msg.chat.id, 'Set log channel for group {}'.format(tgid))

    @bot.message_handler(commands=['unsetlog'])
    def handle_unsetlog(msg):
        admin_ids = [x.user.id for x in bot.get_chat_administrators(msg.chat.id)]
        if msg.chat.type not in ('group', 'supergroup'):
            if msg.from_user.id not in admin_ids:
                # Silently ignore /setlog command from non-admin
                delete_message_safe(msg)
                pass
            else:
                bot.send_message(msg.chat.id, "This command has to be called from a group or a supergroup")
            return

        if msg.from_user.id not in admin_ids:
            if msg.from_user.id not in admin_ids:
                delete_message_safe(msg)
                pass
            else:
                bot.send_message(msg.chat.id, "You are not an administrator")
            return

        set_setting(GROUP_CONFIG, msg.chat.id, 'log_channel_id', None)
        tgid = '@{}'.format(msg.chat.username if msg.chat.username else '#{}'.format(msg.chat.id))
        bot.send_message(msg.chat.id, 'Unset log channel for group {}'.format(tgid))

    @bot.message_handler(content_types=['new_chat_members'])
    def handle_new_chat_members(msg):
        for user in msg.new_chat_members:
            now = datetime.utcnow()
            JOINED_USERS[(msg.chat.id, user.id)] = now
            db.joined_user.find_one_and_update(
                {
                    'chat_id': msg.chat.id,
                    'user_id': user.id,
                },
                {'$set': {
                    'date': now,
                }},
                upsert=True,
            )

    @bot.message_handler(commands=['cybexantispamrealbotset', 'cybexantispamrealbotget'])
    def handle_set_get(msg):
        if msg.chat.type not in ('group', 'supergroup'):
            bot.send_message(msg.chat.id, "This command has to be called from a group")
            return

        admins = bot.get_chat_administrators(msg.chat.id)
        admin_ids = set([x.user.id for x in admins]) | set(SUPERUSER_IDS)
        if msg.from_user.id not in admin_ids:
            delete_message_safe(msg)
            # bot.send_message(msg.chat.id, 'Access denied')
            return
        re_cmd_set = re.compile(r'^/cybexantispamrealbotset (publog|safehours)=(.+)$')
        re_cmd_get = re.compile(r'^/cybexantispamrealbotget (publog|safehours)=()$')
        if msg.text.startswith('/cybexantispamrealbotset'):
            match = re_cmd_set.match(msg.text)
            action = 'SET'
        else:
            match = re_cmd_get.match(msg.text)
            action = 'GET'
        if not match:
            bot.send_message(msg.chat.id, 'Invalid arguments')
            return

        key, val = match.groups()

        if action == 'GET':
            bot.send_message(msg.chat.id, str(get_setting(GROUP_CONFIG, msg.chat.id, key)))
        else:
            if key == 'publog':
                if val in ('yes', 'no'):
                    val_bool = (val == 'yes')
                    set_setting(GROUP_CONFIG, msg.chat.id, key, val_bool)
                    bot.send_message(msg.chat.id, 'Set public_notification to {} for group {}'
                                     .format(val_bool,
                                             '@{}'.format(msg.chat.username if msg.chat.username else '#{}'.format(
                                                 msg.chat.id,
                                             ))))
                else:
                    bot.send_message(msg.chat.id, 'Invalid public_notification value. Should be: yes or no')
            elif key == 'safehours':
                if not val.isdigit():
                    bot.send_message(msg.chat.id, 'Invalid safehours value. Should be a number')
                val_int = int(val)
                max_hours = 24 * 365
                if val_int < 0 or val_int > max_hours:
                    bot.send_message(msg.chat.id,
                                     'Invalid safehours value. Should be a number between 1 and {}'.format(max_hours))
                set_setting(GROUP_CONFIG, msg.chat.id, key, val_int)
                bot.send_message(
                    msg.chat.id,
                    'Set safehours to {} for group {}'.format(
                        val_int, '{}'.format(
                            msg.chat.username if msg.chat.username else '#{}'.format(
                                msg.chat.id,
                            )))
                )
            else:
                bot.send_message(msg.chat.id, 'Unknown action: {}'.format(key))

    @bot.message_handler(commands=['stat'])
    def handle_stat(msg):
        if msg.chat.type != 'private':
            if msg.text.strip() in (
                    '/stat', '/stat@cybexantispamrealbot', '/stat@cybexantispamrealtestbot',
            ):
                bot.delete_message(msg.chat.id, msg.message_id)
            return
        days = []
        s_days = {
            'delete_sticker': 0,
            'delete_document': 0,
            'delete_photo': 0,
            'delete_audio': 0,
            'delete_voice': 0,
            'delete_video': 0,
            'delete_location': 0,
            'delete_contact': 0,
            'delete_video_note': 0,
            'delete_link': 0
        }
        top_today = Counter()
        top_ystd = Counter()
        top_week = Counter()
        types = ['delete_sticker', 'delete_document', 'delete_photo', 'delete_audio',
                 'delete_voice', 'delete_video', 'delete_location', 'delete_contact',
                 'delete_video_note', 'delete_link']
        today = datetime.utcnow().replace(hour=0, minute=0, second=0, microsecond=0)
        for x in range(7):
            day = today - timedelta(days=x)
            for t_type in types:
                res = db.event.find({'$and': [{'type': t_type}, ]})._Cursor__spec['$and'][0]["type"]
                if res in types:
                    s_days[res] += 1
                query = {'$and': [
                    {'type': t_type},
                    {'date': {'$gte': day}},
                    {'date': {'$lt': day + timedelta(days=1)}},
                ]}
                num = 0
                for event in db.event.find(query):
                    num += 1
                    key = (
                        '@{}'.format(event['chat_username']) if event['chat_username']
                        else '#{}'.format(event['chat_id'])
                    )
                    if day == today:
                        top_today[key] += 1
                    if day == (today - timedelta(days=1)):
                        top_ystd[key] += 1
                    top_week[key] += 1
                days.insert(0, num)
        ret = 'STATS \n'
        for t_type in types:
            if s_days[t_type] != 0:
                ret += '\nThe number of {} deleted this week were {}'.format(
                    t_type, s_days[t_type])
            else:
                ret += 'Nothing was deleted this week'
            # ret = 'Recent 7 days: {}'.format(' | '.join([str(x) for x in days]))
        ret += '\n\nTop today ({}):\n{}'.format(
            len(top_today),
            '\n'.join('  %s (%d)' % x for x in top_today.most_common()
                      ))
        ret += '\n\nTop yesterday (%d):\n%s' % (
            len(top_ystd),
            '\n'.join('  %s (%d)' % x for x in top_ystd.most_common()
                      ))
        ret += '\n\nTop 10 week:\n%s' % '\n'.join('  %s (%d)' % x for x in top_week.most_common(10))
        bot.reply_to(msg, ret)

    def format_user_display_name(user):
        if user.first_name and user.last_name:
            return '{} {}'.format(
                user.first_name,
                user.last_name,
            )
        elif user.first_name:
            return user.first_name
        elif user.username:
            return user.first_name
        else:
            return '#{}'.format(user.id)

    def log_event_to_channel(msg, reason, chid, formats):
        if msg.chat.username:
            from_chatname = '<a href="https://t.me/{}">@{}</a>'.format(
                msg.chat.username, msg.chat.username
            )
        else:
            from_chatname = '#{}'.format(msg.chat.id)
        user_display_name = format_user_display_name(msg.from_user)
        from_info = (
            'Chat: {}\nUser: <a href=tg://user?id={}">{}</a>'.format(
                from_chatname, msg.from_user.id, user_display_name)
        )
        # if 'forward' in formats:
        #     try:
        #         msg.forward_message(
        #             chid, msg.chat.id, msg.message_id
        #         )
        #     except Exception or AttributeError as ex:
        #         db.fail.save({
        #             'date': datetime.utcnow(),
        #             'reason': str(ex),
        #             'traceback': format_exc(),
        #             'chat_id': msg.chat.id,
        #             'msg_id': msg.message_id,
        #         })
        #         if (
        #                 'MESSAGE_ID_INVALID' in str(ex) or
        #                 'message to forward not found' in str(ex)
        #         ):
        #             logging.error(
        #                 'Failed to forward spam message: {}'.format(ex)
        #             )
        #         else:
        #             raise

        if 'json' in formats:
            # TODO to_dict() and jsondate may cause an error
            msg_dump = msg.to_dict()
            msg_dump['meta'] = {
                'reason': reason,
                'date': datetime.utcnow(),
            }
            dump = jsondate.dumps(msg_dump, indent=4, ensure_ascii=False)
            dump = html.escape(dump)
            content = '{}\n<pre>{}</pre>'.format(from_info, dump)
            try:
                bot.reply_to(chid, content, parse_mode='HTML')
            except Exception as ex:
                if 'message is too long' in str(ex):
                    logging.error('Failed to log message to channel: {}'.format(ex))
                else:
                    raise
            if 'simple' in formats:
                text = html.escape(msg.text or msg.caption)
                content = (
                    '{}\nReason: {}\nContent:\n<pre>{}</pre>'.format(
                        from_info, reason, text)
                )
                bot.reply_to(chid, content, parse_mode='HTML')

    def delete_message_safe(msg):
        try:
            bot.delete_message(msg.chat.id, msg.message_id)
        except Exception as ex:
            if (
                    'message tp delete not found' in str(ex)
                    # or "message can\'t be deleted" in str(ex)
                    or "be deleted" in str(ex)
                    # fix
                    or "MESSAGE_ID_INVALID" in str(ex)
            ):
                pass
            else:
                raise

    def _run_main(msg, bool, reason):
        """
        :param bool: bool
        :param reason: str
        """
        if msg.chat.type in ('channel', 'private'):
            return
        if bool:
            try:
                user_display_name = format_user_display_name(msg.from_user)
                event_key = (msg.chat.id, msg.from_user.id)
                if get_setting(GROUP_CONFIG, msg.chat.id, 'publog', True):
                    # Notify about spam from same user one time per hour
                    if (
                            event_key not in DELETE_EVENTS
                            or DELETE_EVENTS[event_key] <
                            (datetime.utcnow() - timedelta(hours=1))
                    ):
                        ret = 'Removed msg from <i>{}</i>. Reason: new user + {}'.format(
                            html.escape(user_display_name), reason
                        )
                        bot.reply_to(msg.chat.id, ret, parse_mode='HTML')
                DELETE_EVENTS[event_key] = datetime.utcnow()

                ids = {GLOBAL_LOG_CHANNEL_ID['production']}
                channel_id = get_setting(
                    GROUP_CONFIG, msg.chat.id, 'log_channel_id'
                )
                if channel_id:
                    ids.add(channel_id)
                for chid in ids:
                    formats = get_setting(
                        GROUP_CONFIG, chid, 'logformat', default=['simple']
                    )
                    try:
                        log_event_to_channel(msg, reason, chid, formats)
                    except Exception or AttributeError:
                        logging.exception(
                            'Failed to send notification to channel [{}]'.format(chid)
                        )
            except Exception or AttributeError as ex:
                logging.error('Failed to process spam message: {}'.format(
                    ex))

    @bot.message_handler(func=lambda msg: True)
    def handle_all_messages(msg):
        if msg.chat.type in ('channel', 'private'):
            return
        to_delete, reason = get_delete_link(msg)
        if to_delete:
            try:
                bot.delete_message(msg.chat.id, msg.message_id)
            except Exception or AttributeError as ex:
                db.fail.save({
                    'date': datetime.utcnow(),
                    'reason': str(ex),
                    'traceback': format_exc(),
                    'chat_id': msg.chat.id,
                    'msg_id': msg.message_id,
                })
                if (
                        'message to delete not found' in str(ex)
                        # or "message can\'t be deleted" in str(ex)
                        or "be delete" in str(ex)
                        or "MESSAGE_ID_INVALID" in str(ex)
                        or 'message to forward not found' in str(ex)
                ):
                    logging.error('Failed to process spam message: {}'.format(
                        ex))
                else:
                    raise

    return bot


def main():
    parser = ArgumentParser()
    parser.add_argument('--mode')
    opts = parser.parse_args()
    logging.basicConfig(level=logging.DEBUG)
    if opts.mode == 'test':
        token = TELEGRAM_BOT_TOKEN_TEST
    else:
        token = TELEGRAM_BOT_TOKEN_TEST
    db = connect_db()
    bot = create_bot(token, db)
    bot.polling()
    while True:
        try:
            bot.polling(none_stop=True)
        except Exception as e:
            logging.error(e)
            time.sleep(15)


if __name__ == '__main__':
    main()

# daemon = Daemonize(app='cybex', pid=pid, action=main)
# daemon.start()

