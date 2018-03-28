# -*- coding: utf-8 -*-
#
# wat-bridge
# https://github.com/rmed/wat-bridge
#
# The MIT License (MIT)
#
# Copyright (c) 2016 Rafael Medina García <rafamedgar@gmail.com>
#
# Permission is hereby granted, free of charge, to any person obtaining a copy
# of this software and associated documentation files (the "Software"), to deal
# in the Software without restriction, including without limitation the rights
# to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
# copies of the Software, and to permit persons to whom the Software is
# furnished to do so, subject to the following conditions:
#
# The above copyright notice and this permission notice shall be included in all
# copies or substantial portions of the Software.
#
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
# IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
# FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
# AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
# LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
# OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE
# SOFTWARE.

"""Signal handlers."""

import os
import magic
import sys
from telebot import util as tgutil
from wat_bridge.helper import get_contact, get_phone, db_get_group
from wat_bridge.static import SETTINGS, get_logger
from wat_bridge.tg import tgbot
from wat_bridge.wa import wabot

logger = get_logger('signals')

def sigint_handler(signal, frame):
    """Function used as handler for SIGINT to terminate program."""
    sys.exit(0)

def to_tg_handler(sender, **kwargs):
    """Handle signals sent to Telegram.

    This will involve sending messages through the Telegram bot.

    Args:
        phone (str): Phone number that sent the message.
        message (str): The message received
        media (boolean): True or False
    """
    phone = kwargs.get('phone')
    message = kwargs.get('message')
    media = kwargs.get('media')


    # Check if known contact
    contact = get_contact(phone)
    chat_id = SETTINGS['owner']

    if media:
        participant_id, message_url = message.split("=|=|=")
        # Media Messages
        if not contact:
            output = 'Media from #unknown\n'
            output += 'Phone number: %s\n' % phone
            output += 'Participant ID: %s\n' % participant_id
        else:
            group = db_get_group(contact)
            if not group:
                output = 'Media from #%s\n' % contact
                output += 'Participant ID: %s\n' % participant_id
            else:
                # Contact is bound to group
                chat_id = group
                output = "Media from %s\n" % participant_id
        if message_url.startswith("LOCATION=|=|="):
            locstr, lat, lng = message_url.split("=|=|=")
            tgbot.send_message(chat_id, output)
            tgbot.send_location(chat_id, lat, lng)
        # vcard can be handled in a similar manner
        elif message_url.startswith("VCARDCONTACT=|=|="):
            constr, name, cdata = message_url.split("=|=|=")
            # TODO: but How?
        else:
            mime = magic.Magic(mime=True)
            mime_type = mime.from_file(message_url)
            if "image" in mime_type:
                tgbot.send_photo(chat_id, open(message_url, 'rb'), caption=output)
            else:
                tgbot.send_document(chat_id, open(message_url, 'rb'), caption=output)
            os.remove(message_url)
    else:
        # Text Messages
        if not contact:
            # Unknown sender
            output = 'Message from #unknown\n'
            output += 'Phone number: %s\n' % phone
            output += '---------\n'
            output += message

            logger.info('received message from unknown number: %s' % phone)

        else:
            group = db_get_group(contact)
            if not group:
                # Known sender
                output = 'Message from #%s\n' % contact
                output += '---------\n'
                output += message
            else:
                # Contact is bound to group
                chat_id = group
                output = message

            logger.info('received message from %s' % contact)

        # Deliver message through Telegram
        for chunk in tgutil.split_string(output, 3000):
            tgbot.send_message(chat_id, chunk)


def to_wa_handler(sender, **kwargs):
    """Handle signals sent to Whatsapp.

    This will involve sending messages through the Whatsapp bot.

    Args:
        contact (str): Name of the contact to send the message to.
        message (str): The message to send
    """
    contact = kwargs.get('contact')
    message = kwargs.get('message')

    # Check if known contact
    phone = get_phone(contact)

    if not phone:
        # Abort
        tgbot.send_message(
            SETTINGS['owner'],
            'Unknown contact: "%s"' % contact
        )

        return

    logger.info('sending message to %s (%s)' % (contact, phone))

    wabot.send_msg(phone=phone, message=message)
