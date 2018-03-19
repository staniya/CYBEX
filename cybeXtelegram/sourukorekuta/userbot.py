"""The userbot module."""
import getpass
import logging

from telethon import TelegramClient
from telethon.errors import SessionPasswordNeededError
from telethon.tl.functions.channels import GetParticipantsRequest
from telethon.tl.functions.messages import SendMessageRequest
from telethon.tl.types import Channel, InputChannel, ChannelParticipantsSearch, \
    InputPeerChannel, User

import configs

logger = logging.getLogger(__name__)
api_id = configs.ub_api_id
api_hash = configs.ub_api_hash
phone = configs.ub_phone
curdir = '/'.join(__file__.split('/')[:-1]) + '/'
client = TelegramClient(curdir + 'main_session',
                        api_id, api_hash)
client.connect()

if not client.is_user_authorized():
    client.sign_in(phone)
    try:
        client.sign_in(code=input('Enter auth code: '))
    except SessionPasswordNeededError:
        client.sign_in(password=getpass.getpass())


def get_participants_ids(channel: Channel,
                         raw_users: bool = False) -> list:
    channel = InputChannel(channel.id, channel.access_hash)
    result = client(GetParticipantsRequest(channel,
                                           ChannelParticipantsSearch(''),
                                           0,
                                           10000,
                                           None))
    if not raw_users:
        ids = [user.id for user in result.users if not user.bot]
        return ids
    else:
        return result.users


def get_channel(title: str) -> Channel:
    dialogs, chats = client.get_dialogs(10000)
    chat = [a for a in chats
            if isinstance(a, Channel) and title == a.title][0]  # type: Channel
    return chat


def get_participant_by_id(usrid: int, channel: Channel):
    participants = get_participants_ids(channel, raw_users=True)
    user = [user for user in participants if user.id == usrid][0]  # type: User
    return user


def send_message_to_channel(msg: str) -> None:
    chash = 2860610687140429468
    cid = 1113142718
    channel = InputPeerChannel(cid, chash)
    client(SendMessageRequest(channel, msg))
