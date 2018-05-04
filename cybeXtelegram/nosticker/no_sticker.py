import os
import re
from pprint import pprint
from pathlib import Path
from traceback import format_exc
import urllib

import yaml
import html
import sys
import logging
import telebot
from collections import Counter
from argparse import ArgumentParser

from datetime import datetime, timedelta

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
3. Enable only one item: Delete messages
4. Click SAVE button
5. Enjoy!

*Commands*
/help - display this help message
/stat - display simple statistics about number of deleted messages
/cybexantispamrealbot_set publog=[yes|no] - enable/disable messages to group about deleted posts
/cybexantispamrealbot_set safehours=[int] - number in hours, how long new users are restricted to post links and forward posts, default is 24 hours (Allowed value is number between 1 and 8760)
/cybexantispamrealbot_get publog - get value of publog setting
/cybexantispamrealbot_get safehours - get value of safehours setting

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
PATH = os.path.dirname(os.path.abspath(__file__))
config_file = PATH + '/config.yaml'
my_file = Path(config_file)
if my_file.is_file():
    with open(config_file) as fp:
        config = yaml.load(fp)
else:
    pprint('config.yaml file does not exist')
    sys.exit()

# production
BOTNAME = config['BOT_USERNAME']
TELEGRAM_BOT_TOKEN = config['BOT_TOKEN']

# test
BOTNAME_TEST = config['BOT_USERNAME1']
TELEGRAM_BOT_TOKEN_TEST = config['BOT_TOKEN1']

SUPERUSER_IDS = {547143881}
# List of keys allowed to use in set_setting/get_setting
GROUP_SETTING_KEYS = ('publog', 'log_channel_id', 'logformat', 'safehours')
# Channel of global channel to translate ALL spam
GLOBAL_LOG_CHANNEL_ID = {
    'production': -1001313978621
}
# Default time to reject link and forwarded posts from new user
DEFAULT_SAFE_HOURS = 720

# Some shitty global code
JOINED_USERS = {}
GROUP_CONFIG = load_group_config(db=connect_db())
DELETE_EVENTS = {}


def create_bot(api_token, db):
    bot = telebot.TeleBot(api_token)

    @bot.message_handler(content_types=['sticker'])
    def handle_sticker(msg):
        join_date = get_join_date(msg.chat.id, msg.from_user.id)
        if join_date is None:
            return False, None
        safehours = get_setting(
            GROUP_CONFIG, msg.chat.id, 'safehours', DEFAULT_SAFE_HOURS
        )
        if datetime.utcnow() - join_date < timedelta(hours=safehours):
            bot.delete_message(msg.chat.id, msg.message_id)
            db.event.save({
                'type': 'delete_sticker',
                'chat_id': msg.chat.id,
                'chat_username': msg.chat.username,
                'user_id': msg.from_user.id,
                'username': msg.from_user.username,
                'date': datetime.utcnow(),
            })

    @bot.message_handler(content_types=['document'])
    def handle_document(msg):
        join_date = get_join_date(msg.chat.id, msg.from_user.id)
        if join_date is None:
            return False, None
        safehours = get_setting(
            GROUP_CONFIG, msg.chat.id, 'safehours', DEFAULT_SAFE_HOURS
        )
        if datetime.utcnow() - join_date < timedelta(hours=safehours):
            bot.delete_message(msg.chat.id, msg.message_id)
            db.event.save({
                'type': 'delete_document',
                'chat_id': msg.chat.id,
                'chat_username': msg.chat.username,
                'user_id': msg.from_user.id,
                'username': msg.from_user.username,
                'date': datetime.utcnow(),
                'document': {
                    'file_id': msg.document.file_id,
                    'file_name': msg.document.file_name,
                    'mime_type': msg.document.mime_type,
                    'file_size': msg.document.file_size,
                    'thumb': msg.document.thumb.__dict__ if msg.document.thumb else None,
                },
            })

    @bot.message_handler(content_types=['photo'])
    def handle_photo(msg):
        join_date = get_join_date(msg.chat.id, msg.from_user.id)
        if join_date is None:
            return False, None
        safehours = get_setting(
            GROUP_CONFIG, msg.chat.id, 'safehours', DEFAULT_SAFE_HOURS
        )
        if datetime.utcnow() - join_date < timedelta(hours=safehours):
            bot.delete_message(msg.chat.id, msg.message_id)
            db.event.save({
                'type': 'delete_photo',
                'chat_id': msg.chat.id,
                'chat_username': msg.chat.username,
                'user_id': msg.from_user.id,
                'username': msg.from_user.username,
                'date': datetime.utcnow(),
                'photo': {
                    'photo': 'photo_deleted',
                    # TODO how to get the file_id for this one?
                },
            })

    @bot.message_handler(content_types=['audio'])
    def handle_audio(msg):
        join_date = get_join_date(msg.chat.id, msg.from_user.id)
        if join_date is None:
            return False, None
        safehours = get_setting(
            GROUP_CONFIG, msg.chat.id, 'safehours', DEFAULT_SAFE_HOURS
        )
        if datetime.utcnow() - join_date < timedelta(hours=safehours):
            bot.delete_message(msg.chat.id, msg.message_id)
            db.event.save({
                'type': 'delete_audio',
                'chat_id': msg.chat.id,
                'chat_username': msg.chat.username,
                'user_id': msg.from_user.id,
                'username': msg.from_user.username,
                'date': datetime.utcnow(),
                'audio': {
                    'file_id': msg.audio.file_id,
                    'title': msg.audio.title,
                    'file_size': msg.audio.file_size,
                    'performer': msg.audio.performer,
                    'mime_type': msg.audio.mime_type,
                },
            })

    @bot.message_handler(content_types=['voice'])
    def handle_voice(msg):
        join_date = get_join_date(msg.chat.id, msg.from_user.id)
        if join_date is None:
            return False, None
        safehours = get_setting(
            GROUP_CONFIG, msg.chat.id, 'safehours', DEFAULT_SAFE_HOURS
        )
        if datetime.utcnow() - join_date < timedelta(hours=safehours):
            bot.delete_message(msg.chat.id, msg.message_id)
            db.event.save({
                'type': 'delete_voice',
                'chat_id': msg.chat.id,
                'chat_username': msg.chat.username,
                'user_id': msg.from_user.id,
                'username': msg.from_user.username,
                'date': datetime.utcnow(),
                'voice': {
                    'file_id': msg.voice.file_id,
                    'file_size': msg.voice.file_size,
                    'mime_type': msg.voice.mime_type,
                },
            })

    @bot.message_handler(content_types=['video'])
    def handle_video(msg):
        join_date = get_join_date(msg.chat.id, msg.from_user.id)
        if join_date is None:
            return False, None
        safehours = get_setting(
            GROUP_CONFIG, msg.chat.id, 'safehours', DEFAULT_SAFE_HOURS
        )
        if datetime.utcnow() - join_date < timedelta(hours=safehours):
            bot.delete_message(msg.chat.id, msg.message_id)
            db.event.save({
                'type': 'delete_video',
                'chat_id': msg.chat.id,
                'chat_username': msg.chat.username,
                'user_id': msg.from_user.id,
                'username': msg.from_user.username,
                'date': datetime.utcnow(),
                'video': {
                    'file_id': msg.video.file_id,
                    'file_size': msg.video.file_size,
                    'mime_type': msg.video.mime_type,
                },
            })

    @bot.message_handler(content_types=['location'])
    def handle_location(msg):
        join_date = get_join_date(msg.chat.id, msg.from_user.id)
        if join_date is None:
            return False, None
        safehours = get_setting(
            GROUP_CONFIG, msg.chat.id, 'safehours', DEFAULT_SAFE_HOURS
        )
        if datetime.utcnow() - join_date < timedelta(hours=safehours):
            bot.delete_message(msg.chat.id, msg.message_id)
            db.event.save({
                'type': 'delete_location',
                'chat_id': msg.chat.id,
                'chat_username': msg.chat.username,
                'user_id': msg.from_user.id,
                'username': msg.from_user.username,
                'date': datetime.utcnow(),
                'location': {
                    'latitude': msg.location.latitude,
                    'longitude': msg.location.longitude,
                },
            })

    @bot.message_handler(content_types=['contact'])
    def handle_contact(msg):
        join_date = get_join_date(msg.chat.id, msg.from_user.id)
        if join_date is None:
            return False, None
        safehours = get_setting(
            GROUP_CONFIG, msg.chat.id, 'safehours', DEFAULT_SAFE_HOURS
        )
        if datetime.utcnow() - join_date < timedelta(hours=safehours):
            bot.delete_message(msg.chat.id, msg.message_id)
            db.event.save({
                'type': 'delete_contact',
                'chat_id': msg.chat.id,
                'chat_username': msg.chat.username,
                'user_id': msg.from_user.id,
                'username': msg.from_user.username,
                'date': datetime.utcnow(),
                'contact': {
                    'phone_number': msg.contact.phone_number,
                    'first_name': msg.contact.first_name,
                },
            })

    @bot.message_handler(content_types=['video_note'])
    def handle_video_note(msg):
        join_date = get_join_date(msg.chat.id, msg.from_user.id)
        if join_date is None:
            return False, None
        safehours = get_setting(
            GROUP_CONFIG, msg.chat.id, 'safehours', DEFAULT_SAFE_HOURS
        )
        if datetime.utcnow() - join_date < timedelta(hours=safehours):
            bot.delete_message(msg.chat.id, msg.message_id)
            db.event.save({
                'type': 'delete_video_note',
                'chat_id': msg.chat.id,
                'chat_username': msg.chat.username,
                'user_id': msg.from_user.id,
                'username': msg.from_user.username,
                'date': datetime.utcnow(),
                'video_note': {
                    'videonote': 'video note deleted',
                    # TODO get file_id for this one
                },
            })

    # # @bot.message_handler(content_types=['text'])
    # def handle_link(msg):
    #     urls = re.findall('http[s]?://(?:[a-zA-Z]|[0-9]|[$-_@.&+]|[!*\(\),]|(?:%[0-9a-fA-F][0-9a-fA-F]))+', msg.text)
    #     # RE_SIMPLE_LINK = re.compile(
    #     #     r"https?://(?:[-\w.]|(?:%[\da-fA-F]{2}))+",
    #     #     re.X | re.I | re.U
    #     # )
    #     if urls:
    #         bot.delete_message(msg.chat.id, msg.message_id)
    #         db.event.save({
    #             'type': 'delete_link',
    #             'chat_id': msg.chat.id,
    #             'chat_username': msg.chat.username,
    #             'user_id': msg.from_user.id,
    #             'username': msg.from_user.username,
    #             'date': datetime.utcnow(),
    #             'link': {
    #                 'links': 'link deleted',
    #             },
    #         })

    @bot.message_handler(commands=['start', 'help'])
    def handle_start_help(msg):
        if msg.chat.type == 'private':
            bot.reply_to(msg, HELP, parse_mode='Markdown')
        else:
            if msg.text.strip() in (
                    '/start', '/start@cybexantispamrealbot', '/start@cybexantispamrealtestbot',
                    '/help', '/help@cybexantispamrealbot', '/help@cybexantispamrealtestbot'
            ):
                bot.delete_message(msg.chat.id, msg.message_id)

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

    def get_delete_reason(msg):
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
                if ent.type in ('url', 'text_link'):
                    return True, 'external link'
                # TODO maybe need to change all of this to True later
                if ent.type in ('email',):
                    return False, 'email'
                if ent.type == 'mention':
                    text = msg.text if scope == 'text' else msg.caption
                    username = text[ent.offset:ent.offset + ent.length].lstrip('@')
                    user_type = process_user_type(username)
                    if user_type in ('group', 'channel'):
                        return False, '@-link to group/channel'
            if msg.forward_from or msg.forward_from_chat:
                return False, 'forwarded'
            return False, None

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

    @bot.message_handler(commands=['cybexantispamrealbot_set', 'cybexantispamrealbot_get'])
    def handle_set_get(msg):
        if msg.chat.type not in ('group', 'supergroup'):
            bot.send_message(msg.chat.id, "This command has to be called from a group")
            return

        admins = bot.get_chat_administrators(msg.chat.id)
        admin_ids = set([x.user.id for x in admins]) | set(SUPERUSER_IDS)
        if msg.from_user.id not in admin_ids:
            bot.delete_message(msg.chat.id, msg.message_id)
            # bot.send_message(msg.chat.id, 'Access denied')
            return
        re_cmd_set = re.compile(r'^/cybexantispamrealbot_set (publog|safehours)=(.+)$')
        re_cmd_get = re.compile(r'^/cybexantispamrealbot_get (publog|safehours)=()$')
        if msg.text.startswith('/cybexantispamrealbot_set'):
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
        top_today = Counter()
        top_ystd = Counter()
        top_week = Counter()
        today = datetime.utcnow().replace(hour=0, minute=0, second=0, microsecond=0)
        for x in range(7):
            day = today - timedelta(days=x)
            types = ['delete_sticker', 'delete_document', 'delete_photo', 'delete_audio',
                     'delete_voice', 'delete_video', 'delete_location', 'delete_contact',
                     'delete_video_note', 'delete_link']
            # TODO check if this is correct
            for t_type in types:
                query = {'$and': [
                    {'type': t_type},
                    {'date': {'$gte': day}},
                    {'date': {'$lt': day + timedelta(days=1)}},
                ]}
                num = 0
                for event in db.event.find(query):
                    num += 1
                    key = (
                        '@%s' % event['chat_username'] if event['chat_username']
                        else '#%d' % event['chat_id']
                    )
                    if day == today:
                        top_today[key] += 1
                    if day == (today - timedelta(days=1)):
                        top_ystd[key] += 1
                    top_week[key] += 1
                days.insert(0, num)
        ret = 'Recent 7 days: %s' % ' | '.join([str(x) for x in days])
        ret += '\n\nTop today (%d):\n%s' % (
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

    @bot.message_handler(commands=['text'])
    def handle_link(msg):
        if msg.chat.type in ('channel', 'private'):
            return
        to_delete, reason = get_delete_reason(msg)
        if to_delete:
            try:
                db.event.save({
                                'type': 'delete_link',
                                'chat_id': msg.chat.id,
                                'chat_username': msg.chat.username,
                                'user_id': msg.from_user.id,
                                'username': msg.from_user.username,
                                'date': datetime.utcnow(),
                                'link': {
                                    'links': 'link deleted',
                                },
                            })
                user_display_name = format_user_display_name(msg.from_user)
                event_key = (msg.chat.id, msg.from_user.id)
                if get_setting(GROUP_CONFIG, msg.chat.id, 'publog', True):
                    # Notify about spam from same user only one time per hour
                    if (
                            event_key not in DELETE_EVENTS
                            or DELETE_EVENTS[event_key] <
                            (datetime.utcnow() - timedelta(hours=1))
                    ):
                        ret = 'Removed msg from <i>{}</i>. Reason: new user + {}'.format(
                            html.escape(user_display_name), reason
                        )
                        bot.reply_to(msg.chat.id, ret, parse_mode='Markdown')
                DELETE_EVENTS[event_key] = datetime.utcnow()

                # ids = {GLOBAL_LOG_CHANNEL_ID['production']}
                # channel_id = get_setting(
                #     GROUP_CONFIG, msg.chat.id, 'log_channel_id'
                # )
                # if channel_id:
                #     ids.add(channel_id)
                # for chid in ids:
                #     formats = get_setting(
                #         GROUP_CONFIG, chid, 'logformats', default=['simple']
                #     )
                #     try:
                #         log_event_to_channel(bot, msg, reason, chid, formats)
                #     except Exception as ex:
                #         logging.exception(
                #             'Failed to send notification to channel [{}]'.format(
                #                 chid
                #             )
                #         )
            finally:
                try:
                    bot.delete_message(msg.chat.id, msg.message_id)
                except Exception as ex:
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
        token = TELEGRAM_BOT_TOKEN
    db = connect_db()
    bot = create_bot(token, db)
    bot.polling()


if __name__ == '__main__':
    main()
