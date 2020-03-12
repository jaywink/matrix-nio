# -*- coding: utf-8 -*-

# Copyright © 2018, 2019 Damir Jelić <poljar@termina.org.uk>
#
# Permission to use, copy, modify, and/or distribute this software for
# any purpose with or without fee is hereby granted, provided that the
# above copyright notice and this permission notice appear in all copies.
#
# THE SOFTWARE IS PROVIDED "AS IS" AND THE AUTHOR DISCLAIMS ALL WARRANTIES
# WITH REGARD TO THIS SOFTWARE INCLUDING ALL IMPLIED WARRANTIES OF
# MERCHANTABILITY AND FITNESS. IN NO EVENT SHALL THE AUTHOR BE LIABLE FOR ANY
# SPECIAL, DIRECT, INDIRECT, OR CONSEQUENTIAL DAMAGES OR ANY DAMAGES WHATSOEVER
# RESULTING FROM LOSS OF USE, DATA OR PROFITS, WHETHER IN AN ACTION OF
# CONTRACT, NEGLIGENCE OR OTHER TORTIOUS ACTION, ARISING OUT OF OR IN
# CONNECTION WITH THE USE OR PERFORMANCE OF THIS SOFTWARE.

"""Matrix direct messages module.

This module contains classes that can be used to send direct events to a Matrix
homeserver.
"""

from typing import Dict

import attr

from . import EventBuilder


@attr.s
class ToDeviceMessage(EventBuilder):
    """A to-device message that can be sent to the homeserver.

    Attributes:
        type (str): The type of the message.
        recipient (str): The user to whom we should sent this message.
        recipient_device (str): The device id of the device that the message
            should be sent to.
        content (Dict[Any, Any]): The content that should be sent to the user.

    """

    type = attr.ib(type=str)
    recipient = attr.ib(type=str)
    recipient_device = attr.ib(type=str)
    content = attr.ib(type=Dict)

    def as_dict(self):
        return {
            "messages": {
                self.recipient: {
                    self.recipient_device: self.content
                }
            }
        }


@attr.s
class DummyMessage(ToDeviceMessage):
    """A dummy to-device mssage that is sent to restart a Olm session."""
    pass


@attr.s
class RoomKeyRequestMessage(ToDeviceMessage):
    """A to-device message that requests room keys from other devices.

    Attributes:
        request_id (str): The unique request id that identifies this key
            request.
        session_id (str): The session id that uniquely identifies the room key.
        room_id (str): The room id of the room that the key belongs to.
        algorithm (str): The algorithm of the room key.

    """
    request_id = attr.ib(type=str)
    session_id = attr.ib(type=str)
    room_id = attr.ib(type=str)
    algorithm = attr.ib(type=str)