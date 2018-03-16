import threading
from typing import Set
from logging import getLogger

from ehforwarderbot import EFBChannel, EFBMsg, EFBStatus, ChannelType, MsgType, coordinator, EFBChat
from ehforwarderbot.message import EFBMsgLinkAttribute, EFBMsgLocationAttribute
from ehforwarderbot.status import EFBMessageRemoval


class MockMasterChannel(EFBChannel):

    channel_name: str = "Mock Master"
    channel_emoji: str = "➕"
    channel_id: str = "tests.mocks.master"
    channel_type: ChannelType = ChannelType.Master
    supported_message_types: Set[MsgType] = {MsgType.Text, MsgType.Link}
    __version__: str = '0.0.1'

    # Slave-only methods
    get_chat = None
    get_chats = None
    get_chat_picture = None

    logger = getLogger(channel_id)

    polling = threading.Event()

    def poll(self):
        self.polling.wait()

    def send_status(self, status: EFBStatus):
        self.logger.debug("Received status: %r", status)

    def send_message(self, msg: EFBMsg) -> EFBMsg:
        self.logger.debug("Received message: %r", msg)
        return msg

    def stop_polling(self):
        self.polling.set()

    def send_text_msg(self):
        slave = coordinator.slaves['tests.mocks.slave']
        wonderland = slave.get_chat('wonderland001')
        msg = EFBMsg()
        msg.deliver_to = slave
        msg.chat = wonderland
        msg.author = EFBChat(self).self()
        msg.type = MsgType.Text
        msg.text = "Hello, world."
        return coordinator.send_message(msg)

    def send_link_msg(self):
        slave = coordinator.slaves['tests.mocks.slave']
        alice = slave.get_chat('alice')
        msg = EFBMsg()
        msg.deliver_to = slave
        msg.chat = alice
        msg.author = EFBChat(self).self()
        msg.type = MsgType.Link
        msg.text = "Check it out."
        msg.attributes = EFBMsgLinkAttribute(
            title="Example",
            url="https://example.com"
        )
        return coordinator.send_message(msg)

    def send_location_msg(self):
        slave = coordinator.slaves['tests.mocks.slave']
        alice = slave.get_chat('alice')
        msg = EFBMsg()
        msg.deliver_to = slave
        msg.chat = alice
        msg.author = EFBChat(self).self()
        msg.type = MsgType.Location
        msg.text = "I'm not here."
        msg.attributes = EFBMsgLocationAttribute(latitude=0.1, longitude=1.0)
        return coordinator.send_message(msg)

    def send_message_recall_status(self):
        slave = coordinator.slaves['tests.mocks.slave']
        alice = slave.get_chat('alice')
        msg = EFBMsg()
        msg.deliver_to = slave
        msg.chat = alice
        msg.author = EFBChat(self).self()
        msg.uid = "1"
        status = EFBMessageRemoval(self, slave, msg)
        return coordinator.send_status(status)