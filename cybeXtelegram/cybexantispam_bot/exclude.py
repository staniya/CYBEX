import json
import logging
import telebot
from collections import Counter
from argparse import ArgumentParser
from pymongo import MongoClient
from datetime import datetime, timedelta
# from cybexantispam_bot import TELEGRAM_BOT_TOKEN, TELEGRAM_BOT_TOKEN_TEST


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


def create_bot(api_token, db):
    bot = telebot.TeleBot(api_token)

    @bot.message_handler(content_types=['sticker'])
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
                'photo': 'photo_deleted',
                # TODO how to get the file_id for this one?
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

    @bot.message_handler(commands=['start', 'help'])
    def handle_start_help(msg):
        if msg.chat.type == 'private':
            bot.reply_to(msg, HELP, parse_mode='Markdown')
        else:
            if msg.text.strip() in (
                    '/start', '/start@cybexantispam_bot', '/start@cybexantispam_test_bot',
                    '/help', '/help@cybexantispam_bot', '/help@cybexantispam_test_bot'
            ):
                bot.delete_message(msg.chat.id, msg.message_id)

    @bot.message_handler(commands=['stat'])
    def handle_stat(msg):
        if msg.chat.type != 'private':
            if msg.text.strip() in (
                    '/stat', '/stat@cybexantispam_bot', '/stat@cybexantispam_test_bot',
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
            query = {'$and': [
                {'type': 'delete_sticker'},
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

    return bot


def main():
    parser = ArgumentParser()
    parser.add_argument('--mode')
    opts = parser.parse_args()
    logging.basicConfig(level=logging.DEBUG)
    if opts.mode == 'test':
        token = '589779835:AAF_0bncAaeB7qRngj5AoC74Zh_ax8k23h0'
    else:
        token = '547236194:AAE6wmCcTXdlUseg01LA3yWaooX3HFC9gB8'
    db = MongoClient()['nosticker']
    bot = create_bot(token, db)
    bot.polling()


if __name__ == '__main__':
    main()
