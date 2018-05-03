import re

import telebot
from datetime import datetime, timedelta


def create_bot(api_token, db):
    # TODO add a link function here too
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

    @bot.message_handler(content_types=['text'])
    def handle_link(msg):
        urls = re.findall('http[s]?://(?:[a-zA-Z]|[0-9]|[$-_@.&+]|[!*\(\),]|(?:%[0-9a-fA-F][0-9a-fA-F]))+', msg.text)
        # RE_SIMPLE_LINK = re.compile(
        #     r"https?://(?:[-\w.]|(?:%[\da-fA-F]{2}))+",
        #     re.X | re.I | re.U
        # )
        if urls:
            bot.delete_message(msg.chat.id, msg.message_id)
            db.event.save({
                'type': 'delete_link',
                'chat_id': msg.chat.id,
                'chat_username': msg.chat.username,
                'user_id': msg.from_user.id,
                'username': msg.from_user.username,
                'date': datetime.utcnow(),
                'link': {
                    'links': 'link deleted',
                },
            })
    return bot
