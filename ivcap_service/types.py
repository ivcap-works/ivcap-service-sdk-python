#
# Copyright (c) 2025 Commonwealth Scientific and Industrial Research Organisation (CSIRO). All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file. See the AUTHORS file for names of contributors.
#
import os
from dataclasses import dataclass
from typing import TYPE_CHECKING, Any, BinaryIO, cast

from ivcap_client.ivcap import IVCAP
from pydantic import BaseModel, ConfigDict, Field, PrivateAttr, field_validator

from .events import EventReporter

if TYPE_CHECKING:
    import openai

# Default LLM model to use when a service/caller doesn't specify one
# explicitly (e.g. 'LlmTester.model' in 'ivcap_service.testkit.llm'). Can be
# overridden by setting the 'DEFAULT_LLM_MODEL' environment variable, e.g. to
# point a deployment at a different default model without code changes.
DEFAULT_LLM_MODEL = os.environ.get("DEFAULT_LLM_MODEL", "sciansa-default")

# Local fallback for an OpenAI API key, used by 'JobContext.llm_client()'
# when 'OPENAI_API_KEY' isn't set (and no 'api_key' kwarg/'LITELLM_PROXY' is
# in play either) - handy for local development without exporting
# environment variables. A single plain text file containing just the key,
# stripped of surrounding whitespace.
_OPENAI_API_KEY_FILE = os.path.expanduser("~/.config/openai/api_key")


def _read_openai_api_key_file() -> str | None:
    """Read the local OpenAI API key fallback file (see
    '_OPENAI_API_KEY_FILE'). Returns None (rather than raising) when the
    file doesn't exist or is empty, so the caller can decide what to do
    next."""
    try:
        with open(_OPENAI_API_KEY_FILE, encoding="utf-8") as f:
            value = f.read().strip()
    except OSError:
        return None
    return value or None


class ExecutionContext:
    pass


class JobContext(BaseModel):
    job_id: str
    report: EventReporter
    job_authorization: str | None = None

    _ivcap: IVCAP | None = PrivateAttr(None)

    model_config = ConfigDict(arbitrary_types_allowed=True)

    @property
    def ivcap(self) -> IVCAP:
        if self._ivcap is None:
            self._ivcap = cast(IVCAP, IVCAP())
        return self._ivcap

    def llm_client(self, **kwargs: Any) -> "openai.OpenAI":
        """Return an OpenAI-compatible client, ready to use.

        This hides the details of how/whether to route completions through a
        LiteLLM proxy from the service code, and resolves the API key in the
        following order (first match wins):

        1. An explicit 'api_key' kwarg passed in here.
        2. 'LITELLM_PROXY' environment variable - if set, 'base_url' is
           pointed at that proxy's '/v1' endpoint and a placeholder
           'api_key' is used (the proxy itself handles
           authentication/authorization), so no real key is needed.
        3. 'OPENAI_API_KEY' environment variable - the usual variable read
           by a plain 'openai.OpenAI()' client ('OPENAI_BASE_URL' is used
           the same way for the endpoint).
        4. '~/.config/openai/api_key' - a plain text file containing just
           the key, as a local-development fallback for when you don't want
           to export environment variables.

        If none of the above yields a key (and 'LITELLM_PROXY' isn't set,
        since no key is needed in that case), a 'RuntimeError' is raised
        with guidance on how to configure one.

        Any 'kwargs' passed in are forwarded to 'openai.OpenAI(...)' and take
        precedence over everything above (e.g. pass 'base_url=...' to
        override the endpoint too).

        See also 'DEFAULT_LLM_MODEL' for the default model name to pass to
        e.g. 'client.chat.completions.create(model=..., ...)' when the
        caller/request doesn't specify one.

        Requires the optional 'openai' package to be installed.
        """
        try:
            import openai
        except ImportError as e:
            raise ImportError(
                "The 'openai' package is required to use JobContext.llm_client(). "
                "Install it with e.g. 'pip install openai'."
            ) from e

        base_url = os.getenv("LITELLM_PROXY")
        if base_url is not None:
            kwargs.setdefault("base_url", f"{base_url}/v1")
            kwargs.setdefault("api_key", "not-needed")
        elif "api_key" not in kwargs and not os.getenv("OPENAI_API_KEY"):
            api_key = _read_openai_api_key_file()
            if api_key is None:
                raise RuntimeError(
                    "No OpenAI API key found. Set the 'OPENAI_API_KEY' environment "
                    f"variable, write the key to '{_OPENAI_API_KEY_FILE}', or pass "
                    "'api_key=...' to 'llm_client()' directly."
                )
            kwargs["api_key"] = api_key
        return openai.OpenAI(**kwargs)


@dataclass
class BinaryResult:
    """If the result of the tool is a non json serialisable object, return an
    instance of this class indicating the content-type and the actual
    result either as a byte array or a file handle to a binary content (`open(..., "rb")`)"""

    content_type: str = Field(description="Content type of result serialised")
    content: bytes | str | BinaryIO = Field(
        description="Content to send, either as byte array or file handle"
    )


@dataclass
class IvcapResult(BinaryResult):
    isError: bool = False
    raw: Any = None


class ExecutionError(BaseModel):
    """
    Pydantic model for execution errors.
    """

    jschema: str = Field(
        default="urn:ivcap:schema.service.error.1",
        validation_alias="$schema",
        serialization_alias="$schema",
    )
    error: str = Field(description="Error message")
    type: str = Field(description="Error type")
    traceback: str | None = Field(default=None, description="traceback")

    model_config = {
        "populate_by_name": True,
    }


def with_schema(schema_uri: str):
    def decorator(cls):
        class _SchemaField(BaseModel):
            schema_: str = Field(default=schema_uri, alias="$schema")
            model_config = {"populate_by_name": True, "serialize_by_alias": True}

            @field_validator("schema_")
            @classmethod
            def _check_schema(cls, v):
                if v != schema_uri:
                    raise ValueError(f"$schema must be {schema_uri!r}, got {v!r}")
                return v

        Wrapped = type(
            cls.__name__, (cls, _SchemaField), {"__module__": cls.__module__}
        )
        Wrapped.__qualname__ = getattr(cls, "__qualname__", cls.__name__)
        return Wrapped

    return decorator
