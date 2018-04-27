#!/usr/bin/env python
from collections import Counter
import re
import jsondate
import json
import logging
import telebot
from argparse import ArgumentParser
from datetime import datetime, timedelta
import html
import time
from traceback import format_exc
from itertools import chain
from functools import partial

from pymongo import MongoClient
from telegram import ParseMode, Bot
from telegram.ext import Updater, CommandHandler, MessageHandler, Filters, RegexHandler
from telegram.error import TelegramError
from telegram.ext.dispatcher import run_async

from model import load_group_config
from util import find_username_links, find_external_links, fetch_user_type
from database import connect_db


HELP = """*No Sticker Bot Help*

This simple telegram bot was created to solve only one task - to delete FUCKINGLY annoying stickers. Since you add bot to the group and allow it to sticker messages it starts deleting any sticker posted to the group.

*Usage*

1. Add [@nosticker_bot](https://t.me/nosticker_bot) to your group.
2. Go to group settings / users list / promote user to admin
3. Enable only one item: Delete messages
4. Click SAVE button
5. Enjoy!

*Commands*

/help - display this help message
/stat - display simple statistics about number of deleted stickers

*Questions, Feedback*

Support group: [@tgrambots](https://t.me/tgrambots)
"""

########## code imported from daysandbx_bot.py ############

SUPERUSER_IDS = {547143881, 483171166}
# List of keys allowed to use in set_setting/get_setting
GROUP_SETTING_KEYS = ('publog', 'log_channel_id', 'logformat', 'safe_hours')
# Channel of global channel to translate ALL spam
GLOBAL_LOG_CHANNEL_ID = {
    'production': -1001313978621,
    'test': -1001283245540,
}
# Default time to reject link and forwarded posts from new user
DEFAULT_SAFE_HOURS = 720
db = connect_db()

# Some shitty global code
JOINED_USERS = {}
GROUP_CONFIG = load_group_config(db)
DELETE_EVENTS = {}


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


def save_message_event(db, event_type, msg, **kwargs):
    event = msg.to_dict()
    event.update({
        'date': datetime.utcnow(),
        'type': event_type,
    })
    event.update(**kwargs)
    db.event.save(event)


def delete_message_safe(bot, msg):
    try:
        bot.delete_message(msg.chat.id, msg.message_id)
    except Exception as ex:
        if (
                'message to delete not found' in str(ex)
                # or "message can\'t be deleted" in str(ex)
                or "be deleted" in str(ex)  # quick fix
                or "MESSAGE_ID_INVALID" in str(ex)
        ):
            pass
        else:
            raise


def set_setting(db, group_config, group_id, key, val):
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


def process_user_type(db, username):
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


@run_async
def handle_new_chat_members(bot, update):
    msg = update.message
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


@run_async
def handle_start_help(bot, update):
    msg = update.effective_message
    save_message_event(db, 'start_help', msg)
    if msg.chat.type == 'private':
        bot.send_message(
            msg.chat.id,
            HELP,
            parse_mode=ParseMode.MARKDOWN,
            disable_web_page_preview=True
        )
    else:
        if msg.text.strip() in (
                '/start', '/start@cybexantispam_bot', '/start@cybexantispam_test_bot',
                '/help', '/help@cybexantispam_bot', '/help@cybexantispam_test_bot'
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


@run_async
def handle_set_get(bot, update):
    msg = update.effective_message
    if msg.chat.type not in ('group', 'supergroup'):
        bot.send_message(msg.chat.id, "This command has to be called from a group")
        return

    admins = bot.get_chat_administrators(msg.chat.id)
    admin_ids = set([x.user.id for x in admins]) | set(SUPERUSER_IDS)
    if msg.from_user.id not in admin_ids:
        delete_message_safe(bot, msg)
        # bot.send_message(msg.chat.id, 'Access denied')
        return
    re_cmd_set = re.compile(r'^/cybexantispam_set (publog|safe_hours)=(.+)$')
    re_cmd_get = re.compile(r'^/cybexantispam_get (publog|safe_hours)=()$')
    if msg.text.startswith('/cybexantispam_set'):
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
                set_setting(db, GROUP_CONFIG, msg.chat.id, key, val_bool)
                bot.send_message(msg.chat.id, 'Set public_notification to {} for group {}'
                                 .format(val_bool,
                                         '@{}'.format(msg.chat.username if msg.chat.username else '#{}'.format(
                                             msg.chat.id,
                                         ))))
            else:
                bot.send_message(msg.chat.id, 'Invalid public_notification value. Should be: yes or no')
        elif key == 'safe_hours':
            if not val.isdigit():
                bot.send_message(msg.chat.id, 'Invalid safe_hours value. Should be a number')
            val_int = int(val)
            max_hours = 24 * 365
            if val_int < 0 or val_int > max_hours:
                bot.send_message(msg.chat.id,
                                 'Invalid safe_hours value. Should be a number between 1 and {}'.format(max_hours))
            set_setting(db, GROUP_CONFIG, msg.chat.id, key, val_int)
            bot.send_message(
                msg.chat.id,
                'Set safe_hours to {} for group {}'.format(
                    val_int, '{}'.format(
                        msg.chat.username if msg.chat.username else '#{}'.format(
                            msg.chat.id,
                        )))
            )
        else:
            bot.send_message(msg.chat.id, 'Unknown action: {}'.format(key))


@run_async
def handle_setlogformat(bot, update):
    msg = update.effective_message
    # possible options:
    # /setlogformat [json|forward]*

    if msg.chat.type != 'channel':
        admin_ids = [x.user.id for x in bot.get_chat_administrators(msg.chat.id)]
        if msg.from_user.id not in admin_ids:
            # Silently ignore /setlogformat command from non-admin in non-channel
            delete_message_safe(bot, msg)
        else:
            bot.send_message(msg.chat.id, 'This comand has to be called from a channel')
        return
    valid_formats = ('json', 'forward', 'simple')
    formats = msg.text.split(' ')[-1].split(',')
    if any(x not in valid_formats for x in formats):
        bot.send_message(msg.chat.id, 'Invalid arguments. Valid choices: {}'.format(
            ', '.join(valid_formats),))
        return
    set_setting(db, GROUP_CONFIG, msg.chat.id, 'logformat', formats)
    bot.send_message(msg.chat.id, 'Set logformat for this channel')


@run_async
def handle_setlog(bot, update):
    msg = update.effective_message
    admin_ids = [x.user.id for x in bot.get_chat_administrators(msg.chat.id)]
    if msg.chat.type not in ('group', 'supergroup'):
        bot.send_message(msg.chat.id, 'This command has to be called from the group')
        return
    if not msg.forward_from_chat or msg.forward_from_chat.type != 'channel':
        if msg.from_user.id not in admin_ids:
            # Silently ignore /setlog command from non-admin
            delete_message_safe(bot, msg)
            pass
        else:
            bot.send_message(msg.chat.id, 'Command /setlog must be forwarded from channel')
            return
        channel = msg.forward_from_chat
        if bot.get_me().id not in admin_ids:
            bot.send_message(msg.chat.id, 'Assign me as an admin in the chat')
            return

        if msg.from_user.id not in admin_ids:
            delete_message_safe(bot, msg)
            # bot.send_message(msg.chat.id, 'Access denied')
            return

        set_setting(db, GROUP_CONFIG, msg.chat.id, 'log_channel_id', channel.id)
        tgid = '@{}'.format(msg.chat.username if msg.chat.username else '#{}'.format(msg.chat.id))
        bot.send_message(msg.chat.id, 'Set log channel for group {}'.format(tgid))


@run_async
def handle_unsetlog(bot, update):
    msg = update.effective_message
    admin_ids = [x.user.id for x in bot.get_chat_administrators(msg.chat.id)]
    if msg.chat.type not in ('group', 'supergroups'):
        if msg.from_user.id not in admin_ids:
            # Silently ignore /setlog command from non-admin
            delete_message_safe(bot, msg)
            pass
        else:
            bot.send_message(msg.chat.id, 'This command has to be called from a group')
        return

    if msg.from_user.id not in admin_ids:
        if msg.from_user.id not in admin_ids:
            # Silently ignore /setlog command from non-admin
            delete_message_safe(bot, msg)
            pass
        else:
            bot.send_message(msg.chat.id, 'Access denied')
        return

    set_setting(db, GROUP_CONFIG, msg.chat.id, 'log_channel_id', None)
    tgid = '@{}'.format(msg.chat.username if msg.chat.username else '#{}'.format(msg.chat.id))
    bot.send_message(msg.chat.id, 'Unset log channel for group {}'.format(tgid))


def get_delete_reason(msg):
    if (
        msg.from_user.username == 'Shinno'
        and (msg.text == 'del' or msg.caption == 'del')
    ):
        return True, 'debug delete'
    join_date = get_join_date(msg.chat.id, msg.from_user.id)
    if join_date is None:
        return False, None
    safe_hours = get_setting(
        GROUP_CONFIG, msg.chat.id, 'safe_hours', DEFAULT_SAFE_HOURS
    )
    if datetime.utcnow() - timedelta(hours=safe_hours) > join_date:
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
                user_type = process_user_type(db, username)
                if user_type in ('group', 'channel'):
                    return True, '@-link to group/channel'
        if msg.forward_from or msg.forward_from_chat:
            return True, 'forwarded'
        return False, None


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


def log_event_to_channel(bot, msg, reason, chid, formats):
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
    if 'forward' in formats:
        try:
            bot.forward_message(
                chid, msg.chat.id, msg.message_id
            )
        except Exception as ex:
            db.fail.save({
                'date': datetime.utcnow(),
                'reason': str(ex),
                'traceback': format_exc(),
                'chat_id': msg.chat.id,
                'msg_id': msg.message_id,
            })
            if (
                'MESSAGE_ID_INVALID' in str(ex) or
                'message to forward not found' in str(ex)
            ):
                logging.error(
                    'Failed to forward spam message: {}'.format(ex)
                )
            else:
                raise
    if 'json' in formats:
        msg_dump = msg.to_dict()
        msg_dump['meta'] = {
            'reason': reason,
            'date': datetime.utcnow(),
        }
        dump = jsondate.dumps(msg_dump, indent=4, ensure_ascii=False)
        dump = html.escape(dump)
        content = '{}\n<pre>{}</pre>'.format(from_info, dump)
        try:
            bot.send_message(chid, content, parse_mode=ParseMode.HTML)
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
            bot.send_message(chid, content, parse_mode=ParseMode.HTML)


@run_async
def handle_any_message(mode, bot, update):
    msg = update.effective_message
    if msg.chat.type in ('channel', 'private'):
        return

    to_delete, reason = get_delete_reason(msg)
    if to_delete:
        try:
            save_message_event(db, 'delete_msg', msg, reason=reason)
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
                    bot.send_message(
                        msg.chat.id, ret, parse_mode=ParseMode.HTML
                    )
            DELETE_EVENTS[event_key] = datetime.utcnow()

            ids = {GLOBAL_LOG_CHANNEL_ID[mode]}
            channel_id = get_setting(
                GROUP_CONFIG, msg.chat.id, 'log_channel_id'
            )
            if channel_id:
                ids.add(channel_id)
            for chid in ids:
                formats = get_setting(
                    GROUP_CONFIG, chid, 'logformats', default=['simple']
                )
                try:
                    log_event_to_channel(bot, msg, reason, chid, formats)
                except Exception as ex:
                    logging.exception(
                        'Failed to send notification to channel [{}]'.format(
                            chid
                        )
                    )
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


def create_bot(api_token, db):
    bot = telebot.TeleBot(api_token)

    @bot.message_handler(
        content_types=['audio', 'document', 'photo',
                       'sticker', 'video', 'voice', 'location'])
    @bot.message_handler(
        content_types=['sticker'])
    def handle_sticker(msg):
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
        bot.delete_message(msg.chat.id, msg.message_id)
        db.event.save({
            'type': 'delete_photo',
            'chat_id': msg.chat.id,
            'chat_username': msg.chat.username,
            'user_id': msg.from_user.id,
            'username': msg.from_user.username,
            'date': datetime.utcnow(),
            'photo': {
                'file_id': msg.photosize.file_id,
                'file_size': msg.photosize.file_size,
            },
        })

    @bot.message_handler(content_types=['audio'])
    def handle_audio(msg):
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
        bot.delete_message(msg.chat.id, msg.message_id)
        db.event.save({
            'type': 'delete_audio',
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
    def handle_voice(msg):
        bot.delete_message(msg.chat.id, msg.message_id)
        db.event.save({
            'type': 'delete_audio',
            'chat_id': msg.chat.id,
            'chat_username': msg.chat.username,
            'user_id': msg.from_user.id,
            'username': msg.from_user.username,
            'date': datetime.utcnow(),
            'video': {
                'file_id': msg.video.file_id,
                'file_size': msg.video.file_size,
                'mime_type': msg.video.mime_type,
                'thumb': msg.video.thumb,
            },
        })

    @bot.message_handler(content_types=['location'])
    def handle_location(msg):
        bot.delete_message(msg.chat.id, msg.message_id)
        db.event.save({
            'type': 'delete_audio',
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


def get_token(mode):
    assert mode in ('test', 'production')
    with open('var/config.json') as inp:
        config = json.load(inp)
    if mode == 'test':
        return config["cybexUserRestrictionTestBot"]['test_api_token']
    else:
        return config["cybexUserRestrictionBot"]['api_token']


def init_updater_with_mode(mode):
    assert mode in ('test', 'production')
    token = Updater(token=get_token(mode), workers=32)
    db = connect_db
    create_bot(token, db)
    return token


def init_bot_with_mode(mode):
    assert mode in ('test', 'production')
    token = Bot(token=get_token(mode))
    db = connect_db
    create_bot(token, db)
    return token


def register_handlers(dispatcher, mode):
    assert mode in ('production', 'test')

    dispatcher.add_handler(MessageHandler(
        Filters.status_update.new_chat_members, handle_new_chat_members
    ))
    dispatcher.add_handler(CommandHandler(
        ['start', 'help'], handle_start_help
    ))
    dispatcher.add_handler(CommandHandler('stat', handle_stat))
    dispatcher.add_handler(CommandHandler(
        ['cybexantispam_set', 'cybexantispam_get'], handle_set_get
    ))
    dispatcher.add_handler(CommandHandler('setlog', handle_setlog))
    dispatcher.add_handler(CommandHandler('unsetlog', handle_unsetlog))
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


if __name__ == '__main__':
    main()
