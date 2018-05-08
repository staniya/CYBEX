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
from telegram.ext import Updater, CommandHandler, MessageHandler, Filters
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
    re_cmd_set = re.compile(r'^/cybexantispamset (publog|safehours)=(.+)$')
    re_cmd_get = re.compile(r'^/cybexantispamget (publog|safehours)=()$')
    if msg.text.startswith('/cybexantispamset'):
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
        elif key == 'safehours':
            if not val.isdigit():
                bot.send_message(msg.chat.id, 'Invalid safehours value. Should be a number')
            val_int = int(val)
            max_hours = 24 * 365
            if val_int < 0 or val_int > max_hours:
                bot.send_message(msg.chat.id,
                                 'Invalid safehours value. Should be a number between 1 and {}'.format(max_hours))
            set_setting(db, GROUP_CONFIG, msg.chat.id, key, val_int)
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


def get_token(mode):
    assert mode in ('test', 'production')
    if mode == 'test':
        return TELEGRAM_BOT_TOKEN_TEST
    else:
        return TELEGRAM_BOT_TOKEN


def init_updater_with_mode(mode):
    assert mode in ('test', 'production')
    # TODO deal with the create_bot function later
    # db = connect_db()
    # create_bot(TELEGRAM_BOT_TOKEN, db)
    return Updater(token=get_token(mode), workers=32)


def init_bot_with_mode(mode):
    assert mode in ('test', 'production')
    # db = connect_db()
    # create_bot(TELEGRAM_BOT_TOKEN, db)
    return Bot(token=get_token(mode))


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
        ['cybexantispamset', 'cybexantispamget'], handle_set_get
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
