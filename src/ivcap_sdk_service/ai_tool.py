from argparse import ArgumentError, ArgumentParser
import os
import sys
import json
from logging import Logger
from typing import Any, Callable, ClassVar, Generic, Type as TypeT, TypeVar, Union, Optional, Sequence
from typing_extensions import Self
from pydantic import Field, PrivateAttr, field_serializer, model_validator
from argparse import ArgumentError

from ivcap_sdk_service.config import Command

from .cio.io_adapter import IOReadable, IOWritable, OnCloseF, QueueMessage
from .aspect import Aspect
from .service import BaseService, Type, BaseParameter
from .itypes import URN, ServiceArgs
from .ivcap import get_config
from .utils import get_banner
from .config import Config
from .logger import logger, sys_logger
from .itypes import SupportedMimeTypes
from .function import FunctionRequest, FunctionService, T, U

A = TypeVar('A', bound=Aspect)
S = TypeVar('S', bound=Aspect)


class AITool(FunctionService, Generic[A, S, T, U]):
    action: TypeT[A] = Field(description="aspect describing the tool's action")
    service: TypeT[S] = Field(None, description="dataclass describing the service props")

    @model_validator(mode='before')
    def create_request(args: dict) -> dict:
        name = args.get("name", "???")
        action = args.get("action", None)
        service = args.get("service", None)
        def create_request(args: dict) -> dict:
            nonlocal action, service

            d = {}
            a = args.get("action", None)
            if a:
                d["action"] = action(**a)

            if service:
                s = args.get("service", {})
                d["service"] = service(**a)
            return d

        class Request(FunctionRequest, Generic[A, S]):
            SCHEMA: ClassVar[str] = f"urn:sd.platform:schema:ai-tool.request.{name}.1"
            action: A
            service: S = None

            @model_validator(mode='before')
            def create_request2(args: dict) -> dict:
                return create_request(args)

        args["request"] = Request # (action=args.get("action", None), service=args.get("service", None))
        return args

    def _append_sys_arguments(self, ap: ArgumentParser) -> ArgumentParser:
        ap.add_argument("--ivcap:print-ai-tool-description",
            action='store_true',
            help="Print AI Tool description")
        return super()._append_sys_arguments(ap)

    def _get_command(self, cfg: Config) -> Optional[Command]:
        """Return the command to execute or None if it has been taken care of
        """
        if not cfg.CUSTOM_ARGS.get("ivcap:print_ai_tool_description"):
            return super()._get_command(cfg)

        print(json.dumps({
            "$schema": "urn:sd.platform:schema:ai-tool.1",
            "name": self.name,
            "description": self.description,
            "action_schema":  self.action.json_schema(exclude_entity=True),
            "service_schema": self.service.json_schema(exclude_entity=True),
        }, indent=2))
        return None

class AIRequest(FunctionRequest, Generic[A, S]):
    SCHEMA: ClassVar[str] = f"urn:sd.platform:schema:ai-tool.request.unknown.1"
    action: TypeT[A]
    service: TypeT[S]

    @model_validator(mode='before')
    def create_request2(args: dict) -> dict:
        print(">>>>>>>>>>")
        return []

class AIRequest2(Aspect):
    SCHEMA: ClassVar[str] = f"urn:sd.platform:schema:ai-tool.request.unknown.1"

    @model_validator(mode='before')
    def create_request2(args: dict) -> dict:
        print(">>>>>>>>>>")
        return []
