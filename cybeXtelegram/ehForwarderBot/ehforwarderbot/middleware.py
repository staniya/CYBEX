# coding=utf-8

from abc import ABC
from typing import Optional

from .message import EFBMsg
from .status import EFBStatus

__all__ = ['EFBMiddleware']


class EFBMiddleware(ABC):
    """
    Middleware class.

    Attributes:
        middleware_id (str):
            Unique ID of the middleware.
            Convention of IDs is specified in :doc:`/guide/packaging`.
            This ID will be appended with its instance ID when available.
        middleware_name (str): Human-readable name of the middleware.
        instance_id (str):
            The instance ID if available.
    """
    middleware_id: str = "efb.empty_middleware"
    middleware_name: str = "Empty Middleware"
    instance_id: str = None
    __version__: str = 'undefined version'

    def __init__(self, instance_id: str = None):
        """
        Initialize the middleware.
        Inherited initializer must call the "super init" method
        at the beginning.

        Args:
            instance_id: Instance ID of the middleware.
        """
        self.instance_id = instance_id
        if instance_id:
            self.middleware_id += f"#{instance_id}"

    def process_message(self, message: EFBMsg) -> Optional[EFBMsg]:
        """
        Process a message with middleware

        Args:
            message (:obj:`.EFBMsg`): Message object to process

        Returns:
            Optional[:obj:`.EFBMsg`]: Processed message or None if discarded.
        """
        return message

    def process_status(self, status: EFBStatus) -> Optional[EFBStatus]:
        """
        Process a status update with middleware

        Args:
            status (:obj:`.EFBStatus`): Message object to process

        Returns:
            Optional[:obj:`.EFBStatus`]: Processed status or None if discarded.
        """
        return status
