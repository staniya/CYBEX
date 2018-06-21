import os
import re
from pprint import pprint
from pathlib import Path
try:
    from urllib import quote, urlopen
except ImportError:
    from urllib.parse import quote
    from urllib.request import urlopen
import yaml
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

*cybexantispam_bot deletes all posts by users that joined less than a set time period that contain:*
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
/cybexantispamrealbotset safehours=[int] - number in hours, how long new users are restricted to post links and forward posts, default is 168 hours (Allowed value is number between 1 and 8760)
/cybexantispamget publog - get value of publog setting
/cybexantispamget safehours - get value of safehours setting

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
    562854035,
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

    def simplification(msg):
        if (
                msg.from_user.username == 'Shinno1002'
                and (msg.text == 'del' or msg.caption == 'del')
        ):
            return _run_main(msg, True)
        join_date = get_join_date(msg.chat.id, msg.from_user.id)
        if join_date is None:
            now = datetime.utcnow()
            JOINED_USERS[(msg.chat.id, msg.from_user.id)] = now
            db.joined_user.find_one_and_update(
                {
                    'chat_id': msg.chat.id,
                    'user_id': msg.from_user.id,
                },
                {'$set':
                    {
                        'date': now,
                    }},
                upsert=True,
            )
            try:
                bot.delete_message(msg.chat.id, msg.message_id)
                logging.info("No join_date")
                return _run_main(msg, True)
            except Exception or AttributeError as ex:
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
        safehours = get_setting(
            GROUP_CONFIG, msg.chat.id, 'safehours', DEFAULT_SAFE_HOURS
        )
        if datetime.utcnow() - timedelta(hours=safehours) > join_date:
            logging.error("User has been in the chat longer than the set safe hours")
            return _run_main(msg, False)
        else:
            try:
                if msg.from_user.id not in SUPERUSER_IDS:
                    bot.delete_message(msg.chat.id, msg.message_id)
                    return _run_main(msg, True)
                else:
                    return _run_main(msg, False)
            except Exception or AttributeError as ex:
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

    @bot.message_handler(content_types=['sticker'])
    def handle_sticker(msg):
        if (
                msg.from_user.username == 'Shinno1002'
                and (msg.text == 'del' or msg.caption == 'del')
        ):
            return _run_main(msg, True)
        join_date = get_join_date(msg.chat.id, msg.from_user.id)
        if join_date is None:
            logging.error("No join_date")
            return _run_main(msg, False)
        safehours = get_setting(
            GROUP_CONFIG, msg.chat.id, 'safehours', DEFAULT_SAFE_HOURS
        )
        if datetime.utcnow() - timedelta(hours=safehours) > join_date:
            logging.error("User has been in the chat longer than the set safe hours")
            return _run_main(msg, False)
        else:
            return _run_main(msg, False)

    @bot.message_handler(content_types=['document'])
    def handle_document(msg):
        simplification(msg)

    @bot.message_handler(content_types=['photo'])
    def handle_photo(msg):
        simplification(msg)

    @bot.message_handler(content_types=['audio'])
    def handle_audio(msg):
        simplification(msg)

    @bot.message_handler(content_types=['voice'])
    def handle_voice(msg):
        simplification(msg)

    @bot.message_handler(content_types=['video'])
    def handle_video(msg):
        simplification(msg)

    @bot.message_handler(content_types=['location'])
    def handle_location(msg):
        simplification(msg)

    @bot.message_handler(content_types=['contact'])
    def handle_contact(msg):
        simplification(msg)

    @bot.message_handler(content_types=['video_note'])
    def handle_video_note(msg):
        simplification(msg)

    @bot.message_handler(commands=['start', 'help'])
    def handle_start_help(msg):
        if msg.chat.type == 'private':
            if msg.from_user.id not in SUPERUSER_IDS:
                delete_message_safe(msg)
                bot.send_message(msg.chat.id, 'You need to be an administrator to use this command')
            else:
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
                msg.from_user.username == 'Shinno1002'
                and (msg.text == 'del' or msg.caption == 'del')
        ):
            return True, 'debug delete'
        join_date = get_join_date(msg.chat.id, msg.from_user.id)
        if join_date is None:
            now = datetime.utcnow()
            JOINED_USERS[(msg.chat.id, msg.from_user.id)] = now
            db.joined_user.find_one_and_update(
                {
                    'chat_id': msg.chat.id,
                    'user_id': msg.from_user.id,
                },
                {'$set':
                    {
                        'date': now,
                    }},
                upsert=True,
            )
            try:
                bot.delete_message(msg.chat.id, msg.message_id)
                logging.info("No join_date")
                return True, None
            except Exception or AttributeError as ex:
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
                if ent.type in ('email',):
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
                {'$set':
                    {
                        'date': now
                    }},
                upsert=True,
            )

    @bot.message_handler(commands=['cybexantispamrealbotset', 'cybexantispamrealbotget'])
    def handle_set_get(msg):
        if msg.chat.type not in ('group', 'supergroup'):
            bot.send_message(msg.chat.id, "This command has to be called from a group or a supergroup")
            return

        admins = bot.get_chat_administrators(msg.chat.id)
        admin_ids = set([x.user.id for x in admins]) | set(SUPERUSER_IDS)
        if msg.from_user.id not in admin_ids:
            delete_message_safe(msg)
            # bot.send_message(msg.chat.id, 'You need to be an administrator to use this command')
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

    def _run_main(msg, bool):
        """
        :param bool: bool
        """
        if msg.chat.type in ('channel', 'private'):
            return
        if bool:
            try:
                event_key = (msg.chat.id, msg.from_user.id)
                DELETE_EVENTS[event_key] = datetime.utcnow()
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
    while True:
        try:
            bot.polling(none_stop=True)
        except Exception as e:
            logging.error(e)
            time.sleep(15)


if __name__ == '__main__':
    main()
