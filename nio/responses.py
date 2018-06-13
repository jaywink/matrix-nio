# -*- coding: utf-8 -*-

# Copyright © 2018 Damir Jelić <poljar@termina.org.uk>
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

from __future__ import unicode_literals

from typing import *
from typing import NamedTuple

from jsonschema.exceptions import SchemaError, ValidationError
from logbook import Logger

from .api import Api
from .log import logger_group
from .schemas import validate_json, Schemas

logger = Logger('nio.responses')
logger_group.add_logger(logger)


RoomInfo = NamedTuple("RoomInfo", [
    ("invite", dict),
    ("join", dict),
    ("leave", dict)
])

Timeline = NamedTuple(
    "Timeline",
    [
        ("events", list),
        ("limited", bool),
        ("prev_batch", str)
    ]
)

JoindedInfo = NamedTuple(
    "JoinedInfo",
    [
        ("timeline", Timeline),
        ("state", list),
    ]
)


class Event(object):
    def __init__(self, event_id, sender, server_ts):
        # type: (str, str, int) -> None
        self.event_id = event_id
        self.sender = sender
        self.server_timestamp = server_ts


class BadEvent(Event):
    def __init__(self, event_id, sender, server_ts, event_type, source):
        # type: (str, str, int, str, str) -> None
        self.source = source
        self.type = event_type
        super(BadEvent, self).__init__(event_id, sender, server_ts)

    def __str__(self):
        return "Bad event of type {}, from {}.".format(
            self.sender,
            self.type
        )

    @classmethod
    def from_dict(cls, parsed_dict):
        return cls(
            parsed_dict["event_id"],
            parsed_dict["sender"],
            parsed_dict["origin_server_ts"],
            parsed_dict["type"],
            Api.to_json(parsed_dict)
        )


class RedactedEvent(Event):
    def __init__(
        self,
        event_id,    # type: str
        sender,      # type: str
        server_ts,   # type: int
        event_type,  # type: str
        redacter,    # type: str
        reason=None  # type: Optional[str]
    ):
        # type: (...) -> None
        self.event_type = event_type
        self.redacter = redacter
        self.reason = reason
        super(RedactedEvent, self).__init__(event_id, sender, server_ts)

    def __str__(self):
        reason = ", reason: {}".format(self.reason) if self.reason else ""
        return "Redacted event of type {}, by {}{}.".format(
            self.event_type,
            self.redacter,
            reason
        )

    @classmethod
    def from_dict(cls, parsed_dict):
        try:
            validate_json(parsed_dict, Schemas.redacted_event)
        except (ValidationError, SchemaError):
            return BadEvent.from_dict(parsed_dict)

        redacter = parsed_dict["unsigned"]["redacted_because"]["sender"]
        content_dict = parsed_dict["unsigned"]["redacted_because"]["content"]
        reason = content_dict["reason"] if "reason" in content_dict else None

        return cls(
            parsed_dict["event_id"],
            parsed_dict["sender"],
            parsed_dict["origin_server_ts"],
            parsed_dict["type"],
            redacter,
            reason
        )


class RoomMessage(Event):
    @staticmethod
    def from_dict(parsed_dict, olm=None):
        # type: (Dict[Any, Any], Any) -> Union[Event, BadEvent]
        try:
            validate_json(parsed_dict, Schemas.room_message)
        except (SchemaError, ValidationError):
            return BadEvent.from_dict(parsed_dict)

        content_dict = parsed_dict["content"]

        if content_dict["msgtype"] == "m.text":
            return RoomMessageText.from_dict(parsed_dict)

        # TODO return unknown msgtype event
        return None


class RoomMessageText(Event):
    def __init__(
        self,
        event_id,        # type: str
        sender,          # type: str
        server_ts,       # type: int
        body,            # type: str
        formatted_body,  # type: Optional[str]
        body_format      # type: Optional[str]
    ):
        # type: (...) -> None
        super(RoomMessageText, self).__init__(event_id, sender, server_ts)
        self.body = body
        self.formatted_body = formatted_body
        self.format = body_format

    def __str__(self):
        # type: () -> str
        return "{}: {}".format(self.sender, self.body)

    @classmethod
    def from_dict(cls, parsed_dict):
        # type: (Dict[Any, Any]) -> Union[RoomMessageText, BadEvent]
        try:
            validate_json(parsed_dict, Schemas.room_message_text)
        except (SchemaError, ValidationError):
            return BadEvent.from_dict(parsed_dict)

        body = parsed_dict["content"]["body"]
        formatted_body = (parsed_dict["content"]["formatted_body"] if
                          "formatted_body" in parsed_dict["content"] else None)
        body_format = (parsed_dict["content"]["format"] if
                       "format" in parsed_dict["content"] else None)

        return cls(
            parsed_dict["event_id"],
            parsed_dict["sender"],
            parsed_dict["origin_server_ts"],
            body,
            formatted_body,
            body_format
        )


class Response(object):
    pass


class ErrorResponse(Response):
    def __init__(self, message, code=""):
        # type: (str, Optional[str]) -> None
        self.message = message
        self.code = code

    def __str__(self):
        # type: () -> str
        return "Error: {}".format(self.message)

    @classmethod
    def from_dict(cls, parsed_dict):
        # type: (Dict[Any, Any]) -> ErrorResponse
        try:
            validate_json(parsed_dict, Schemas.error)
        except (SchemaError, ValidationError):
            return cls("Unknown error")

        return cls(parsed_dict["error"], parsed_dict["errcode"])


class LoginResponse(Response):
    def __init__(self, user_id, device_id, access_token):
        # type: (str, str, str) -> None
        self.user_id = user_id
        self.device_id = device_id
        self.access_token = access_token

    def __str__(self):
        # type: () -> str
        return "Logged in as {}, device id: {}.".format(
            self.user_id,
            self.device_id
        )

    @classmethod
    def from_dict(cls, parsed_dict):
        # type: (Dict[Any, Any]) -> Union[LoginResponse, ErrorResponse]
        try:
            validate_json(parsed_dict, Schemas.login)
        except (SchemaError, ValidationError):
            return ErrorResponse.from_dict(parsed_dict)

        return cls(parsed_dict["user_id"],
                   parsed_dict["device_id"],
                   parsed_dict["access_token"])


class SyncRepsponse(Response):
    def __init__(self, next_batch, rooms, partial):
        # type: (str, RoomInfo, bool) -> None
        self.next_batch = next_batch
        self.rooms = rooms
        self.partial = partial

    def __str__(self):
        # type: () -> str
        room_messages = []
        for room_id, room_info in self.rooms.join.items():
            room_header = "  Messages for room {}:\n    ".format(room_id)
            messages = []
            for event in room_info.timeline.events:
                messages.append(str(event))

            room_message = room_header + "\n    ".join(messages)
            room_messages.append(room_message)

        body = "\n".join(room_messages)
        string = ("Sync response until batch: {}:\n{}").format(
            self.next_batch,
            body
        )
        return string

    @staticmethod
    def _get_event(event_dict, olm=None):
        pass

    @staticmethod
    def _get_room_events(parsed_dict, max_events=0, olm=None):
        # type: (Dict[Any, Any], int, Any) -> List[Any]
        events = []  # type: List[Any]

        for event_dict in parsed_dict:
            try:
                validate_json(event_dict, Schemas.room_event)

                if "unsigned" in event_dict:
                    if "redacted_because" in event_dict["unsigned"]:
                        events.append(RedactedEvent.from_dict(event_dict))
                        continue

                if event_dict["type"] == "m.room.message":
                    events.append(RoomMessage.from_dict(event_dict, olm))

            except (SchemaError, ValidationError) as e:
                print(e)
                pass

        return events

    @staticmethod
    def _get_timeline(parsed_dict, max_events=0, olm=None):
        # type: (Dict[Any, Any], int, Any) -> Timeline
        validate_json(parsed_dict, Schemas.room_timeline)

        events = SyncRepsponse._get_room_events(
            parsed_dict["events"],
            max_events,
            olm
        )

        return Timeline(
            events,
            parsed_dict["limited"],
            parsed_dict["prev_batch"]
        )

    @staticmethod
    def _get_room_info(parsed_dict, max_events=0, olm=None):
        # type: (Dict[Any, Any], int, Any) -> RoomInfo
        joined_rooms = {
            key: None for key in parsed_dict["join"].keys()
        }  # type: Dict[str, Optional[JoindedInfo]]
        invited_rooms = {}  # type: Dict[str, Any]
        left_rooms = {}  # type: Dict[str, Any]

        for room_id, room_dict in parsed_dict["join"].items():
            timeline = SyncRepsponse._get_timeline(room_dict["timeline"])
            state = []  # type: List[Any]
            info = JoindedInfo(
                timeline,
                state,
            )
            joined_rooms[room_id] = info

        return RoomInfo(invited_rooms, joined_rooms, left_rooms)

    @classmethod
    def from_dict(
        cls,
        parsed_dict,   # type: Dict[Any, Any]
        max_events=0,  # type: int
        olm=None       # type: Any
    ):
        # type: (...) -> Union[SyncRepsponse, ErrorResponse]
        partial = False

        try:
            logger.info("Validating sync response schema")
            validate_json(parsed_dict, Schemas.sync)
            rooms = SyncRepsponse._get_room_info(
                parsed_dict["rooms"],
                max_events,
                olm
            )
        except (SchemaError, ValidationError) as e:
            logger.error("Error validating sync response: " + str(e.message))
            return ErrorResponse.from_dict(parsed_dict)

        return cls(parsed_dict["next_batch"],
                   rooms, partial)