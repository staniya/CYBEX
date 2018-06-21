import os
from collections import Counter
from pprint import pprint
from pathlib import Path

import itertools

import re
import schedule
import yaml
import sys
import logging
from argparse import ArgumentParser
import telebot
from datetime import datetime, timedelta
import time
from database_member_count import connect_db

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

HELP = """
*Group Chat Info Help*

*Displays number of users in a group, supergroup, or channel*

*Commands*
/help - display this help message

*Questions, Feedback*
Support chat - [@Administrators](https://t.me/joinchat/IJzAyRFXj_C42lkLd8iVWQ)
Author's telegram -  [@Shinno](https://t.me/Shinno1002)
Use github issues to report bugs - [github issues](https://github.com/staniya/CYBEX/issues)
"""

ALL_LINKS = {}
db = connect_db()
SUPERUSER_IDS = {
    547143881,
}
links = {}


def create_bot(api_token, db):
    bot = telebot.TeleBot(api_token)

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
                    '/start', '/start@memberCountApebot', '/start@memberCountApeTestbot',
                    '/help', '/help@memberCountApebot', '/help@memberCountApeTestbot'
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

    def set_link(link):
        now = datetime.utcnow()
        ALL_LINKS[link] = now

        #TODO have to change msg.chat.id to link
        number_users = bot.get_chat_members_count(link)
        try:
            db.user_numbers.find_one_and_update(
                {
                    'link': link,
                },
                {'$set':
                    {
                        'date': now,
                        'number': number_users,
                    }},
                upsert=True,
            )
            db.links.save({
                'link_name': link,
            })
        except Exception as ex:
            logging.error('Failed to save link: {}'.format(str(ex)))

    @bot.message_handler(commands=['link'])
    def get_join_date(msg):
        global match, action
        if msg.chat.type != 'private':
            if msg.text.strip in (
                    'link', '/link@memberCountApebot', '/link@memberCountApeTestbot',
            ):
                bot.delete_message(msg.chat.id, msg.message_id)
                return
        if msg.from_user.id not in SUPERUSER_IDS:
            delete_message_safe(msg)
            bot.send_message(msg.chat.id, 'You need to be an administrator to use this command')
            return
        re_cmd_link = re.compile(
            r'^/link (save)=(?:(?:@|＠)(?!\/))([a-zA-Z0-9/_.\-!@#$%&^*]{1,100})(?:\b(?!@|＠)|$)')
        if msg.text.startwith('/link'):
            match = re_cmd_link.match(msg.text)
            action = 'SET'
        if not match:
            bot.send_message(msg.chat.id, 'Invalid arguments')
            return
        key, val = match.groups()

        if action == 'SET':
            if key == 'save':
                locations = [
                    ('text', msg.entities or []),
                    ('caption', msg.caption_entities or []),
                ]
                for scope, entities in locations:
                    for ent in entities:
                        if ent.type in ('url', 'text_link', 'mention'):
                            link = str(val)
                            set_link(link)
                            bot.send_message(msg.chat.id, 'Group {} successfully set'
                                             .format(link))
                        else:
                            bot.send_message(msg.chat.id, "Invalid link. Should be a proper link")
            else:
                bot.send_message(msg.chat.id, 'Unknown action {}'.format(key))

    @bot.message_handler(commands=['getlog'])
    def handle_getlog(msg):
        if msg.chat.type != 'private':
            if msg.text.strip in (
                    '/stat', '/stat@memberCountApebot', '/stat@memberCountApeTestbot',
            ):
                bot.delete_message(msg.chat.id, msg.message_id)
                return
        if msg.from_user.id not in SUPERUSER_IDS:
            delete_message_safe(msg)
            bot.send_message(msg.chat.id, 'You need to be an administrator to use this command')
            return
        days = []
        all_records = Counter()
        today = datetime.utcnow().replace(hour=0, minute=0, second=0, microsecond=0)
        ret = "\n*LOG\n"
        for x in itertools.count():
            day = today - timedelta(days=x)
            names = str(db.links.find({'$and': [{'link_name': {'$ne': None}}, ]}))
            for name in names:
                query = {'$and': [
                    {'link': name},
                    {'date': {'$gte': day}},
                    {'date': {'$lt': day + timedelta(days=1)}},
                ]}
                #TODO get the exact db results for each of the variables
                dates = str(db.user_numbers.find(query))
                num = 0
                if dates is None:
                    bot.send_message(msg.chat.id, "There is no data to be queried")
                else:
                    for event in db.user_numbers.find(query):
                        num += 1
                        key = (
                            '@{}'.format(event['link']) if event['link']
                            else '#{}'.format(event['chat_id'])
                        )
                        all_records[key] += 1
                    days.insert(0, num)
                number = {'$and': [
                    {'link': name},
                    {'number': {'$ne': None}},
                ]}
                var = str(db.user_numbers.find(number))
                if var is None:
                    bot.send_message(msg.chat.id, "There is no data to be queried")
                elif var is True and var not in ret:
                    ret += "\nThere were {} users in chat {} between dates {}"\
                        .format(var, name, dates)
                else:
                    continue
        ret += '\n\nThere are ({}) records in the database right now'.format(
            len(all_records))
        bot.reply_to(msg, ret)

    return bot

def everyday_update():
    names = str(db.links.find({'$and': [{'link_name': {'$ne': None}}, ]}))
    for name in names:



if __name__ == '__main__':
    # logger functions
    logger = logging.getLogger('count')
    logger.setLevel(logging.DEBUG)
    file_handler = logging.FileHandler(config['LOG_FILENAME'])
    file_handler.setLevel(logging.DEBUG)
    logger.addHandler(file_handler)

    # running the telegram bot
    parser = ArgumentParser()
    parser.add_argument('--mode')
    opts = parser.parse_args()
    if opts.mode == 'test':
        token = TELEGRAM_BOT_TOKEN_TEST
    else:
        token = TELEGRAM_BOT_TOKEN
    db = connect_db()
    bot = create_bot(token, db)

    while True:
        try:
            schedule.every(1440).minutes.do(get_join_date(msg))
            bot.polling(none_stop=True)
        except Exception as e:
            logging.error(e)
            time.sleep(15)
