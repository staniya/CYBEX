#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""Basic example for a bot that uses inline keyboards.

# This program is dedicated to the public domain under the CC0 license.
"""
import logging
import os
import yaml
import telegram
import sys
from pprint import pprint

from telegram import InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Updater, CommandHandler, CallbackQueryHandler
from pathlib import Path
from welcomeconversation import gender, name2, photo, location, bio

logging.basicConfig(format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
                    level=logging.INFO)
logger = logging.getLogger(__name__)

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

TELEGRAM_BOT_TOKEN = config['BOT_TOKEN3']
bot = telegram.Bot(token=TELEGRAM_BOT_TOKEN)


def start(bot, update):
    keyboard = [[InlineKeyboardButton("Edit Gender", callback_data='1'),
                 InlineKeyboardButton("Edit Name", callback_data='2')],
                [InlineKeyboardButton("Edit Photo", callback_data='3'),
                 InlineKeyboardButton("Edit Location", callback_data='4')],
                [InlineKeyboardButton("Edit Bio", callback_data='5')]]

    reply_markup = InlineKeyboardMarkup(keyboard)
    update.message.reply_text('Edit User Profile', reply_markup=reply_markup)


def button(bot, update):
    query = update.callback_query

    if query.data == "1":

        gender(bot, update)

        bot.edit_message_text(text="Selected option: {}".format(query.data),
                              chat_id=query.message.chat_id,
                              message_id=query.message.message_id)

    elif query.data == "2":
        bot.edit_message_text(text="Selected option: {}".format(query.data),
                              chat_id=query.message.chat_id,
                              message_id=query.message.message_id)
        return name2

    elif query.data == "3":
        bot.edit_message_text(text="Selected option: {}".format(query.data),
                              chat_id=query.message.chat_id,
                              message_id=query.message.message_id)
        return photo

    elif query.data == "4":
        bot.edit_message_text(text="Selected option: {}".format(query.data),
                              chat_id=query.message.chat_id,
                              message_id=query.message.message_id)
        return location

    elif query.data == "5":
        bot.edit_message_text(text="Selected option: {}".format(query.data),
                              chat_id=query.message.chat_id,
                              message_id=query.message.message_id)
        return bio


def help(bot, update):
    update.message.reply_text("Use /start to test this bot.")


def error(bot, update, error):
    """Log Errors caused by Updates."""
    logger.warning('Update "%s" caused error "%s"', update, error)


def main():
    # Create the Updater and pass it your bot's token.
    updater = Updater(bot=bot)

    updater.dispatcher.add_handler(CommandHandler('start', start))
    updater.dispatcher.add_handler(CallbackQueryHandler(button))
    updater.dispatcher.add_handler(CommandHandler('help', help))
    updater.dispatcher.add_error_handler(error)

    # Start the Bot
    updater.start_polling()

    # Run the bot until the user presses Ctrl-C or the process receives SIGINT,
    # SIGTERM or SIGABRT
    updater.idle()


if __name__ == '__main__':
    main()
