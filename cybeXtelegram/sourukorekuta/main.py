#!/usr/bin/env python
"""The Main bot file."""
import logging
from time import strftime, gmtime
from pathlib import Path
import os
import yaml
from pprint import pprint
import telegram
import sys
from telegram import Bot, Update, Message, Chat, User
from telegram.ext import CommandHandler, Filters, MessageHandler, Updater
import userbot
import configs
import database as db

logging.basicConfig(
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        level=logging.INFO, datefmt='%H:%M:%S', stream=sys.stdout)

logger = logging.getLogger(__name__)

# Configuration

PATH = os.path.dirname(os.path.abspath(__file__))

"""
#	Load the config file
#	Set the Botname / Token
"""
config_file = PATH + '/config.yaml'
my_file = Path(config_file)
if my_file.is_file():
    with open(config_file, encoding="utf-8") as fp:
        config = yaml.load(fp)
else:
    pprint('config.yaml file does not exist.')
    sys.exit()

TELEGRAM_BOT_TOKEN = config['BOT_TOKEN']
bot = telegram.Bot(token=TELEGRAM_BOT_TOKEN)


def msg_type(msg: Message):
    message_type = None
    if msg.entities:
        entity = msg.entities[0].type
        if entity not in ['bold', 'italic', 'code', 'pre', 'text_link']:
            if entity != 'text_mention':
                message_type = entity
            elif entity == 'text_mention':
                message_type = 'mention'
        else:
            message_type = 'text'
    elif msg.photo:
        message_type = 'photo'
    elif msg.sticker:
        message_type = 'sticker'
    elif msg.document:
        filename = msg.document.file_name
        mimetype = msg.document.mime_type
        if filename == 'giphy.mp4':
            message_type = 'gif'
        elif mimetype.split('/')[0] == 'video':
            message_type = 'video'
        else:
            message_type = 'document'
    elif msg.voice:
        message_type = 'voice'
    else:
        message_type = 'text'
    return message_type


def normal_message(bot, update) -> None:
    # python 3 feature allowing you to attach metadata to functions describing parameters and return values
    msg = update.message
    if update.effective_chat.type in ['group', 'supergroup']:
        msgtype = msg_type(msg)
        # msg.reply_text(msgtype)
        db.add_user(update.effective_user)
        db.addgroup(update.effective_chat)
        db.update_user(update.effective_user, update.effective_chat, msgtype)


def check_group(bot: Bot, update: Update) -> None:
    msg = update.effective_message
    for user in msg.new_chat_members:
        if user.id == bot.get_me().id:  # the id of the bot itself
            db.addgroup(update.effective_chat)
        else:
            db.update_user(user,
                           update.effective_chat,
                           "updating",
                           joindate=int(msg.date.timestamp()))


def start(bot: Bot, update: Update) -> None:
    pass


def bothelp(bot: Bot, update: Update) -> None:
    pass


def ping(bot, update) -> None:
    chat = update.effective_chat  # type: Chat
    bot.send_message(chat_id=chat.id, text="MESSAGE")
    if update.effective_chat.type != 'private' and configs.delete_commands:
        bot.delete_message(chat_id=update.effective_chat.id,
                           message_id=update.effective_message.message_id)


def info(bot: Bot, update: Update) -> None:
    chat = update.effective_chat  # type: Chat
    msg = update.effective_message  # type: Message
    usr = update.effective_user  # type: User
    if update.effective_chat.type != 'private':
        if msg.reply_to_message:
            userinfo = db.get_user(bot, msg.reply_to_message.from_user.id,
                                   update.effective_chat.id)
        else:
            userinfo = db.get_user(bot, update.effective_user.id,
                                   update.effective_chat.id)

        msg_list = ["Name: {0} {1}".format(userinfo['first_name'], userinfo['last_name'])]
        if userinfo['username'] != 'None':
            msg_list.append(
                "Username: {0}".format(userinfo['username']))
        if userinfo['joined'] != 'None':
            joined = strftime('%d.%m.%Y', gmtime(int(userinfo['joined'])))
            msg_list.append(
                "Joined: {0}".format(joined)
            )
        msg_list.append(
            "Language: {0}".format(userinfo['language_code'])
        )
        msg_list.append(
            "Status: {0}".format(userinfo['status'])
        )
        msg_list.append(
            "UserID: {0}".format(userinfo['user_id'])
        )
        msg_list.append(
            "Total Messages:".format())
        msg_list.append(
            "Message Types:".format())
        if userinfo['count_text'] != '0':
            msg_list.append(
                "  Texts: {0}".format(userinfo['count_text']))
        if userinfo['count_mention'] != '0':
            msg_list.append(
                "  Mentions: {0}".format(userinfo['count_mention']))
        if userinfo['count_hashtag'] != '0':
            msg_list.append(
                "  Hashtags: {0}".format(userinfo['count_hashtag']))
        if userinfo['count_bot_command'] != '0':
            msg_list.append(
                "  Bot Commands: {0}".format(userinfo['count_bot_command']))
        if userinfo['count_url'] != '0':
            msg_list.append(
                "  URLs: {0}".format(userinfo['count_url']))
        if userinfo['count_email'] != '0':
            msg_list.append(
                "  E-Mails: {0}".format(userinfo['count_email']))
        if userinfo['count_photo'] != '0':
            msg_list.append(
                "  Photos: {0}".format(userinfo['count_photo']))
        if userinfo['count_document'] != '0':
            msg_list.append(
                "  Documents: {0}".format(userinfo['count_document']))
        if userinfo['count_sticker'] != '0':
            msg_list.append(
                "  Stickers: {0}".format(userinfo['count_sticker']))
        if userinfo['count_gif'] != '0':
            msg_list.append(
                "  GIFs: {0}".format(userinfo['count_gif']))
        if userinfo['count_video'] != '0':
            msg_list.append(
                "  Video: {0}".format(userinfo['count_video']))
        if userinfo['count_voice'] != '0':
            msg_list.append(
                "  Voice Messages: {0}".format(userinfo['count_voice']))
        message = '\n'.join(msg_list)
        bot.send_message(chat_id=chat.id, text=message)
        if configs.delete_commands:
            bot.delete_message(chat_id=update.effective_chat.id,
                               message_id=update.effective_message.message_id)


def stats(bot: Bot, update: Update) -> None:
    if update.effective_chat.type != 'private':
        group = db.get_group(update.effective_chat.id)
        groupname = update.effective_chat.title

        update.message.reply_text('This Group has ' + str(group['active_members_count']) +
                                  ' active members')
        if configs.delete_commands:
            bot.delete_message(chat_id=update.effective_chat.id,
                               message_id=update.effective_message.message_id)


def execution_warn(bot: Bot, update: Update) -> None:
    chat = update.effective_chat  # type: Chat
    msg = update.effective_message  # type: Message

    if chat.type != 'private':
        admins = chat.get_administrators()
        admins = [admin.user.id for admin in admins]
        if update.effective_user.id in admins:
            channel = userbot.get_channel(chat.title)
            all_user_ids = userbot.get_participants_ids(channel)
            active_user_ids = db.get_active_user_ids(chat.id)
            lurkers = [lurker for lurker in all_user_ids
                       if lurker not in active_user_ids]
            lurkersmsg = []
            for l in lurkers:
                lurkersmsg.append(
                    "(tg://user?id={0})"
                        .format(bot.get_chat_member(chat.id, l).user.first_name.replace('[', '').replace(']', '')
                                .strip())
                )
            # msg.reply_text(lurkers, parse_mode='Markdown')
            if not lurkersmsg:
                msg.reply_text('There were no inactive members')
                bot.delete_message(chat_id=chat.id, message_id=msg.message_id)
            return
        fullmsg = 'We miss you in our chat, send a cool stamp!'
        bot.send_message(chat_id=chat.id, text=fullmsg, parst_mode='Markdown')
        if configs.delete_commands:
            bot.delete_message(chat_id=chat.id, message_id=msg.message_id)


def error(bot, update, error):
    logger.warning('Update "{0}" caused error "{1}"'.format(update, error))


def main():
    # Create the EventHandler and pass it your bot's token.
    updater = Updater(bot=bot)

    # Get the dispatcher to register handlers
    dp = updater.dispatcher

    # handler to find inactive members
    dp.add_handler(CommandHandler('start', start))
    dp.add_handler(CommandHandler('help', bothelp))
    dp.add_handler(CommandHandler('ping', ping))
    dp.add_handler(CommandHandler(['xinxi', 'info'], info))
    dp.add_handler(CommandHandler(['tongji', 'stats'], stats))
    dp.add_handler(CommandHandler(['lonely', 'executionwarn'],
                                  execution_warn))
    dp.add_handler(MessageHandler(Filters.status_update.new_chat_members,
                                  check_group))
    dp.add_handler(MessageHandler(Filters.all, normal_message))

    # log all errors
    dp.add_error_handler(error)

    # Start the Bot
    updater.start_polling()  # poll_interval=1.0, timeout=20

    # Run the bot until you press Ctrl-C or the process receives SIGINT,
    # SIGTERM or SIGABRT. This should be used most of the time, since
    # start_polling() is non-blocking and will stop the bot gracefully.
    updater.idle()


if __name__ == '__main__':
    main()
