#!/usr/bin/env python3
import logging
import os
from pathlib import Path
import yaml
from pprint import pprint
import sys
import telegram
from html import escape

from emoji import emojize
from telegram import ParseMode, TelegramError, Update
from telegram.ext import Updater, MessageHandler, CommandHandler, Filters
from telegram.ext.dispatcher import run_async

import python3pickledb as pickledb

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

BOTNAME = config['BOT_USERNAME']
TELEGRAM_BOT_TOKEN = config['BOT_TOKEN']
bot = telegram.Bot(token=TELEGRAM_BOT_TOKEN)

help_text = 'This bot will send a welcome message to everyone that enters a group chat that this bot is a ' \
            'part of. By default, only the person who invited the bot into ' \
            'the group is able to change settings.' \
            '\nCommands:\n\n' \
            '/welcome - Set welcome message\n' \
            '/goodbye - Set goodbye message\n' \
            '/disable\\_goodbye - Disable the goodbye message\n' \
            '/lock - Only admin can change messages\n' \
            '/unlock - Everyone can change messages\n' \
            '/quiet - Disable "Sorry, only the person who..." ' \
            '& help messages\n' \
            '/unquiet - Enable "Sorry, only the person who..." ' \
            '& help messages\n\n' \
            'You can use _$username_ and _$title_ as placeholders when setting' \
            ' messages. [HTML formatting]' \
            '(https://core.telegram.org/bots/api#formatting-options) ' \
            'is also supported.\n'
'''
Create database object
Database schema:
<chat_id> -> welcome message
<chat_id>_bye -> goodbye message
<chat_id>_adm -> user id of the user who invited the bot
<chat_id>_lck -> boolean if the bot is locked or unlocked
<chat_id>_quiet -> boolean if the bot is quieted

chats -> list of chat ids where the bot has received messages in.
'''
# Create database object
db = pickledb.load('bot.db', True)

if not db.get('chats'):
    db.set('chats', [])

# Set up logging
root = logging.getLogger()
root.setLevel(logging.INFO)

logging.basicConfig(level=logging.INFO,
                    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')

logger = logging.getLogger(__name__)


@run_async
def send_async(bot, *args, **kwargs):
    bot.sendMessage(*args, **kwargs)


def check(bot, update, override_lock=None):
    """
    Perform some checks on the update. If checks were successful, returns True,
    else sends an error message to the chat and returns False.
    """

    chat_id = update.message.chat_id
    chat_str = str(chat_id)

    if chat_id > 0:
        send_async(bot, chat_id=chat_id,
                   text='Please add me to a group first!')
        return False

    locked = override_lock if override_lock is not None \
        else db.get(chat_str + '_lck')

    if locked and db.get(chat_str + '_adm') != update.message.from_user.id:
        if not db.get(chat_str + '_quiet'):
            send_async(bot, chat_id=chat_id, text='This command is only reserved for the admin.')
        return False

    return True


# Welcome a user to the chat
def welcome(bot, update):
    """ Welcomes a user to the chat """

    message = update.message
    chat_id = message.chat.id
    logger.info('{0} joined to chat {1} ({2})'
                .format(escape(message.new_chat_member.first_name),
                        chat_id,
                        escape(message.chat.title)))

    # Pull the custom message for this chat from the database
    text = db.get(str(chat_id))

    # Use default message if there's no custom one set
    if text is None:
        text = 'Hello $username! Welcome to the Cybex Chat group. Look at the pre-programmed commands for assistance!' \
               ' {0}'.format(emojize(':smile:', use_aliases=True))

    # Replace placeholders and send message
    text = text.replace('$username',
                        message.new_chat_member.first_name) \
        .replace('$title', message.chat.title)
    send_async(bot, chat_id=chat_id, text=text, parse_mode=ParseMode.HTML)


# Welcome a user to the chat
def goodbye(bot, update):
    """ Sends goodbye message when a user left the chat """

    message = update.message
    chat_id = message.chat.id
    logger.info('{0} left chat {1} ({2})'
                .format(escape(message.left_chat_member.first_name),
                        chat_id,
                        escape(message.chat.title)))

    # Pull the custom message for this chat from the database
    text = db.get(str(chat_id) + '_bye')

    # Goodbye was disabled
    if text is False:
        return

    # Use default message if there's no custom one set
    if text is None:
        text = 'Goodbye, $username, it was fun while it lasted!'

    # Replace placeholders and send message
    text = text.replace('$username',
                        message.left_chat_member.first_name) \
        .replace('$title', message.chat.title)
    send_async(bot, chat_id=chat_id, text=text, parse_mode=ParseMode.HTML)


# Introduce the bot to a chat its been added to
def introduce(bot, update):
    """
    Introduces the bot to a chat its been added to and saves the user id of the
    user who invited us.
    """

    chat_id = update.message.chat.id
    invited = update.message.from_user.id

    logger.info('Invited by {0} to chat {1} ({2})'
                .format(invited, chat_id, update.message.chat.title))

    db.set(str(chat_id) + '_adm', invited)
    db.set(str(chat_id) + '_lck', True)

    text = 'Hello {0}! I will now greet anyone who joins this chat with a' \
           ' nice message {1} \nCheck the /help command for more info!' \
        .format(update.message.chat.title,
                emojize(':smile:', use_aliases=True))
    send_async(bot, chat_id=chat_id, text=text)


# Print help text
def help(bot, update):
    """ Prints help text """

    chat_id = update.message.chat.id
    chat_str = str(chat_id)
    if (not db.get(chat_str + '_quiet') or db.get(chat_str + '_adm') ==
            update.message.from_user.id):
        send_async(bot, chat_id=chat_id,
                   text=help_text,
                   parse_mode=ParseMode.MARKDOWN,
                   disable_web_page_preview=True)


# Set custom message
def set_welcome(bot, update, args):
    """ Sets custom welcome message """

    chat_id = update.message.chat.id

    # Check admin privilege and group context
    if not check(bot, update):
        return

    # Split message into words and remove mentions of the bot
    message = ' '.join(args)

    # Only continue if there's a message
    if not message:
        send_async(bot, chat_id=chat_id,
                   text='You need to send a message, too! For example:\n'
                        '<code>/welcome Hello $username, welcome to '
                        '$title!</code>',
                   parse_mode=ParseMode.HTML)
        return

    # Put message into database
    db.set(str(chat_id), message)

    send_async(bot, chat_id=chat_id, text='Got it!')


# Set custom message
def set_goodbye(bot, update, args):
    """ Enables and sets custom goodbye message """

    chat_id = update.message.chat.id

    # Check admin privilege and group context
    if not check(bot, update):
        return

    # Split message into words and remove mentions of the bot
    message = ' '.join(args)

    # Only continue if there's a message
    if not message:
        send_async(bot, chat_id=chat_id,
                   text='You need to send a message, too! For example:\n'
                        '<code>/goodbye Goodbye, $username!</code>',
                   parse_mode=ParseMode.HTML)
        return

    # Put message into database
    db.set(str(chat_id) + '_bye', message)

    send_async(bot, chat_id=chat_id, text='Got it!')


def disable_goodbye(bot, update):
    """ Disables the goodbye message """

    chat_id = update.message.chat.id

    # Check admin privilege and group context
    if not check(bot, update):
        return

    # Disable goodbye message
    db.set(str(chat_id) + '_bye', False)

    send_async(bot, chat_id=chat_id, text='Got it!')


def lock(bot, update):
    """ Locks the chat, so only the invitee can change settings """

    chat_id = update.message.chat.id

    # Check admin privilege and group context
    if not check(bot, update, override_lock=True):
        return

    # Lock the bot for this chat
    db.set(str(chat_id) + '_lck', True)

    send_async(bot, chat_id=chat_id, text='Got it!')


def quiet(bot, update):
    """ Quiets the chat, so no error messages will be sent """

    chat_id = update.message.chat.id

    # Check admin privilege and group context
    if not check(bot, update, override_lock=True):
        return

    # Lock the bot for this chat
    db.set(str(chat_id) + '_quiet', True)

    send_async(bot, chat_id=chat_id, text='Got it!')


def unquiet(bot, update):
    """ Unquiets the chat """

    chat_id = update.message.chat.id

    # Check admin privilege and group context
    if not check(bot, update, override_lock=True):
        return

    # Lock the bot for this chat
    db.set(str(chat_id) + '_quiet', False)

    send_async(bot, chat_id=chat_id, text='Got it!')


def unlock(bot, update):
    """ Unlocks the chat, so everyone can change settings """

    chat_id = update.message.chat.id

    # Check admin privilege and group context
    if not check(bot, update):
        return

    # Unlock the bot for this chat
    db.set(str(chat_id) + '_lck', False)

    send_async(bot, chat_id=chat_id, text='Got it!')


def empty_message(bot, update):
    """
    Empty messages could be status messages, so we check them if there is a new
    group member, someone left the chat or if the bot has been added somewhere.
    """

    # Keep chatlist
    chats = db.get('chats')

    if update.message.chat.id not in chats:
        chats.append(update.message.chat.id)
        db.set('chats', chats)
        logger.info("I have been added to {0} chats".format(len(chats)))

    if update.message.new_chat_member is not None:
        # Bot was added to a group chat
        if update.message.new_chat_member.username == BOTNAME:
            return introduce(bot, update)
        # Another user joined the chat
        else:
            return welcome(bot, update)

    # Someone left the chat
    elif update.message.left_chat_member is not None:
        if update.message.left_chat_member.username != BOTNAME:
            return goodbye(bot, update)


def error(bot, update, error, **kwargs):
    """ Error handling """

    try:
        if isinstance(error, TelegramError) \
                and error.message == "Unauthorized" \
                or "PEER_ID_INVALID" in error.message \
                and isinstance(update, Update):

            chats = db.get('chats')
            chats.remove(update.message.chat_id)
            db.set('chats', chats)
            logger.info('Removed chat_id {0} from chat list'
                        .format(update.message.chat_id))
        else:
            logger.error("An error ({0}) occurred: {1}"
                         .format(type(error), error.message))
    except:
        pass


def main():
    # Create the Updater and pass it your bot's token.
    updater = Updater(bot=bot, workers=10)

    # Get the dispatcher to register handlers
    dp = updater.dispatcher

    dp.add_handler(CommandHandler("start", help))
    dp.add_handler(CommandHandler("help", help))
    dp.add_handler(CommandHandler('welcome', set_welcome, pass_args=True))
    dp.add_handler(CommandHandler('goodbye', set_goodbye, pass_args=True))
    dp.add_handler(CommandHandler('disable_goodbye', disable_goodbye))
    dp.add_handler(CommandHandler("lock", lock))
    dp.add_handler(CommandHandler("unlock", unlock))
    dp.add_handler(CommandHandler("quiet", quiet))
    dp.add_handler(CommandHandler("unquiet", unquiet))

    dp.add_handler(MessageHandler([Filters.status_update], empty_message))

    dp.add_error_handler(error)

    updater.start_polling(timeout=30, clean=False)

    updater.idle()


if __name__ == '__main__':
    main()
