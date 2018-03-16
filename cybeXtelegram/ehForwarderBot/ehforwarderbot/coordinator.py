# coding=utf-8

"""
Coordinator among channels.

Attributes:
    profile (str): Name of current profile..
    mutex (threading.Lock): Global interaction thread lock.
    master (EFBChannel): The running master channel object.
    slaves (Dict[str, EFBChannel]): Dictionary of running slave channel object.
        Keys are the unique identifier of the channel.
    middlewares (List[EFBMiddleware]): List of middlewares
"""

import threading
from typing import List, Dict, Optional

from . import EFBMsg
from .channel import EFBChannel
from .constants import ChannelType
from .exceptions import EFBChannelNotFound
from .middleware import EFBMiddleware
from .status import EFBStatus

profile: str = "default"
"""Current running profile name"""

mutex: threading.Lock = threading.Lock()
"""Mutual exclusive lock for user interaction through CLI interface"""

master: EFBChannel = None
"""The instance of the master channel."""

slaves: Dict[str, EFBChannel] = dict()
"""Instances of slave channels. Keys are the channel IDs."""

middlewares: List[EFBMiddleware] = list()
"""Instances of middlewares. Sorted in the order of execution."""

master_thread: Optional[threading.Thread] = None
"""The thread running poll() of the master channel."""

slave_threads: Dict[str, threading.Thread] = dict()
"""Threads running poll() from slave channels. Keys are the channel IDs."""

translator = None
"""Internal GNU gettext translator."""


def add_channel(channel: EFBChannel):
    """
    Register the channel with the coordinator.

    Args:
        channel (EFBChannel): Channel to register
    """
    global master, slaves
    if isinstance(channel, EFBChannel):
        if channel.channel_type == ChannelType.Slave:
            slaves[channel.channel_id] = channel
        else:
            master = channel
    else:
        raise TypeError("Channel instance is expected")


def add_middleware(middleware: EFBMiddleware):
    """
    Register a middleware with the coordinator.

    Args:
        middleware (EFBMiddleware): Middleware to register
    """
    global middlewares
    if isinstance(middleware, EFBMiddleware):
        middlewares.append(middleware)
    else:
        raise TypeError("Middleware instance is expected")


def send_message(msg: EFBMsg) -> Optional[EFBMsg]:
    """
    Deliver a message to the destination channel.

    Args:
        msg (EFBMsg): The message

    Returns:
        The message sent by the destination channel,
        includes the updated message ID from there.
        Returns ``None`` if the message is not sent.
    """
    global middlewares, master, slaves
    if msg is None:
        return

    # Go through middlewares
    for i in middlewares:
        msg = i.process_message(msg)
        if msg is None:
            return

    msg.verify()

    if msg.deliver_to.channel_id == master.channel_id:
        return master.send_message(msg)
    elif msg.deliver_to.channel_id in slaves:
        return slaves[msg.deliver_to.channel_id].send_message(msg)
    else:
        raise EFBChannelNotFound(msg)


def send_status(status: EFBStatus):
    """
    Deliver a message to the destination channel.

    Args:
        status (EFBStatus): The status
    """
    global middlewares, master
    if status is None:
        return

    # Go through middlewares
    for i in middlewares:
        status = i.process_status(status)
        if status is None:
            return

    status.verify()

    status.destination_channel.send_status(status)
