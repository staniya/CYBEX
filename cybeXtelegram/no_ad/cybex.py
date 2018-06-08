import os
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
import time

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


def create_bot(api_token):
    bot = telebot.TeleBot(api_token)

    def simplification(msg):
        if (
                msg.from_user.username == 'Shinno1002'
                and (msg.text == 'del' or msg.caption == 'del')
        ):
            return _run_main(msg, True)
        else:
            try:
                if msg.from_user.id not in SUPERUSER_IDS:
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

    def get_delete_link(msg):
        if (
                msg.from_user.username == 'Shinno1002'
                and (msg.text == 'del' or msg.caption == 'del')
        ):
            return True, 'debug delete'
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
                    # text = msg.text if scope == 'text' else msg.caption
                    # username = text[ent.offset:ent.offset + ent.length].lstrip('@')
                    # user_type = process_user_type(username)
                    # if user_type in ('group', 'channel'):
                    return False, '@-link to group/channel'
            if msg.forward_from or msg.forward_from_chat:
                return False, 'forwarded'
            return False, None

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
        if msg.chat.type in ('channel', 'private'):
            return
        if bool:
            delete_message_safe(msg)

    @bot.message_handler(func=lambda msg: True)
    def handle_all_messages(msg):
        if msg.chat.type in ('channel', 'private'):
            return
        to_delete, reason = get_delete_link(msg)
        if to_delete:
            delete_message_safe(msg)

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
    bot = create_bot(token)
    while True:
        try:
            bot.polling(none_stop=True)
        except Exception as e:
            logging.error(e)
            time.sleep(15)


if __name__ == '__main__':
    main()

