#!/usr/bin/env python
# -*- coding: utf-8 -*-
#
# Simple Bot to reply to Telegram messages
# This program is dedicated to the public domain under the CC0 license.
"""
Usage:
Example of a bot-user conversation using ConversationHandler.
Send /start to initiate the conversation.
Press Ctrl-C on the command line or send a signal to the process to stop the
bot.
"""
import logging
import sys

import os
from pprint import pprint
from pathlib import Path

import telegram
import yaml
from telegram import (ReplyKeyboardMarkup, ReplyKeyboardRemove)
from telegram.ext import (Updater, CommandHandler, MessageHandler, Filters, RegexHandler,
                          ConversationHandler)

# Enable logging

logging.basicConfig(format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
                    level=logging.INFO, datefmt='%H:%M:%S', stream=sys.stdout)

logger = logging.getLogger(__name__)

GENDER, NAME, NAME2, PHOTO, LOCATION, BIO = range(6)

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

TELEGRAM_BOT_TOKEN = config['BOT_TOKEN1']
bot = telegram.Bot(token=TELEGRAM_BOT_TOKEN)


def login(bot, update):
    reply_keyboard = [['Boy', 'Girl', 'Other']]

    update.message.reply_text(
        'Welcome to CybeX bot! Please answer the following questions. '
        'Send /cancel to stop the conversation.\n\n'
        'Tell me your gender?',
        reply_markup=ReplyKeyboardMarkup(reply_keyboard, one_time_keyboard=True))

    return GENDER


def gender(bot, update):
    user = update.message.from_user
    logger.info("Gender of {0}: {1}".format(user.first_name, update.message.text))
    reply_keyboard = [['Yes', 'No']]
    update.message.reply_text(('Ok! Please tell me if your name is correct: {0}'.format(user.first_name)),
                              reply_markup=ReplyKeyboardMarkup(reply_keyboard, one_time_keyboard=True))

    return NAME


def names(bot, update):
    user = update.message.from_user
    if update.message.text == 'Yes':
        logger.info("Name of user: {0}".format(user.first_name))
        update.message.reply_text('I see! Next, Please send me a photo of yourself, '
                                  'so I know what you look like, or send /skip if you don\'t want to.',
                                  reply_markup=ReplyKeyboardRemove())

        return PHOTO
    else:
        logger.info("{0}".format(update.message.text))
        update.message.reply_text('I\'m sorry I got your name wrong. '
                                  'Would you tell me your first name?',
                                  reply_markup=ReplyKeyboardRemove())
        return NAME2


def name2(bot, update):
    user = update.message.from_user
    updated_first_name = update.message.text
    user.first_name = updated_first_name
    logger.info("Name of user: {0}".format(user.first_name))
    update.message.reply_text('I see! Next, Please send me a photo of yourself, '
                              'so I know what you look like, or send /skip if you don\'t want to.')

    return PHOTO


def photo(bot, update):
    user = update.message.from_user
    photo_file = bot.get_file(update.message.photo[-1].file_id)
    photo_file.download('user_photo.jpg')
    logger.info("Photo of {0}: {1}".format(user.first_name, 'user_photo.jpg'))
    update.message.reply_text('Gorgeous! Now, send me your location please, '
                              'or send /skip if you don\'t want to.')

    return LOCATION


def skip_photo(bot, update):
    user = update.message.from_user
    logger.info("User {0} did not send a photo.".format(user.first_name))
    update.message.reply_text('Ok, you didn\'t want to share a picture. Now, send me your location please, '
                              'or send /skip.')

    return LOCATION


def location(bot, update):
    user = update.message.from_user
    user_location = update.message.location
    logger.info("Location of {0}: {1} / {2}".format(user.first_name, user_location.latitude,
                                                    user_location.longitude))
    update.message.reply_text('Maybe I can visit you sometime! '
                              'At last, tell me something about yourself.')

    return BIO


def skip_location(bot, update):
    user = update.message.from_user
    logger.info("User {0} did not send a location.".format(user.first_name))
    update.message.reply_text('It\'s important to protect your privacy! '
                              'At last, tell me something about yourself.')

    return BIO


def bio(bot, update):
    user = update.message.from_user
    logger.info("Bio of {0}: {1}".format(user.first_name, update.message.text))
    update.message.reply_text('Thank you! I hope we can talk again some day. \n'
                              'To edit any of the information, send /edit')

    return ConversationHandler.END


def cancel(bot, update):
    user = update.message.from_user
    logger.info("User {0} canceled the conversation.".format(user.first_name))
    update.message.reply_text('Bye! I hope we can talk again some day.',
                              reply_markup=ReplyKeyboardRemove())

    return ConversationHandler.END


def error(bot, update, error):
    logger.warning('Update "{0}" caused error "{1}"'.format(update, error))


def main():
    # Create the EventHandler and pass it your bot's token.
    updater = Updater(bot=bot)

    # Get the dispatcher to register handlers
    dp = updater.dispatcher

    # Add conversation handler with the states INITIAL, GENDER, NAME, NAME2, PHOTO, LOCATION, BIO
    conv_handler = ConversationHandler(
        entry_points=[CommandHandler('login', login)],
        states={
            GENDER: [RegexHandler('^(Boy|Girl|Other)$', gender)],

            NAME: [RegexHandler('^(Yes|No)$', names)],

            NAME2: [MessageHandler(Filters.text, name2)],

            PHOTO: [MessageHandler(Filters.photo, photo),
                    CommandHandler('skip', skip_photo)],

            LOCATION: [MessageHandler(Filters.location, location),
                       CommandHandler('skip', skip_location)],

            BIO: [MessageHandler(Filters.text, bio)]
        },

        fallbacks=[CommandHandler('cancel', cancel)]
    )

    dp.add_handler(conv_handler)

    # log all errors
    dp.add_error_handler(error)

    # Start the Bot
    updater.start_polling()

    # Run the bot until you press Ctrl-C or the process receives SIGINT,
    # SIGTERM or SIGABRT. This should be used most of the time, since
    # start_polling() is non-blocking and will stop the bot gracefully.
    updater.idle()


if __name__ == '__main__':
    main()
