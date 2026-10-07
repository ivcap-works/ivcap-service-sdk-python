#
# Copyright (c) 2025 Commonwealth Scientific and Industrial Research Organisation (CSIRO). All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file. See the AUTHORS file for names of contributors.
#
"""
LLM completion worker function (used for the 'llm' section of a
'test-batch' Request).

Getting a pre-configured LLM client
------------------------------------
Every `JobContext` (the `ctxt` argument passed to a service's worker
function) exposes a ready-to-use client via `ctxt.llm_client()`:

    client: openai.OpenAI = ctxt.llm_client()

This returns a plain `openai.OpenAI` instance, already pointed at the
right endpoint:

- If the `LITELLM_PROXY` environment variable is set, the client's
  `base_url` is configured to `{LITELLM_PROXY}/v1` and a placeholder
  `api_key` is used (the proxy itself handles authentication), so your
  service code never needs to know whether requests are routed through
  LiteLLM.
- Otherwise, a standard `openai.OpenAI()` client is returned, relying on
  the usual `OPENAI_API_KEY` / `OPENAI_BASE_URL` environment variables.
- If `OPENAI_API_KEY` isn't set, `~/.config/openai/api_key` (a plain text
  file containing just the key) is read as a final fallback - handy for
  local development where you don't want to export environment variables.
- If no key can be found by any of the above, `llm_client()` raises a
  `RuntimeError` explaining how to configure one.

You can override any of these defaults by passing keyword arguments
straight through to the underlying `openai.OpenAI(...)` constructor, e.g.
`ctxt.llm_client(api_key="sk-...")`.

The `openai` package is an optional dependency - `llm_client()` raises a
clear `ImportError` if it isn't installed, so add `openai` to your
service's dependencies if you intend to call it.

`ivcap_service.DEFAULT_LLM_MODEL` provides a sensible default model name
to pass to `chat.completions.create(model=..., ...)` when the caller
doesn't specify one (as used by `LlmTester.model` below). It defaults to
`"sciansa-default"`, but can be overridden for a whole deployment by
setting the `DEFAULT_LLM_MODEL` environment variable - no code changes
needed.

Using the client
-----------------
Once you have a client, use it exactly like the regular `openai` SDK: call
`client.chat.completions.create(model=..., messages=...)`, where
`messages` is an `Iterable[ChatCompletionMessageParam]` (a list of
per-role dicts such as `{"role": "user", "content": "..."}`). See
`completion()` below for a minimal, complete example that:

1. Obtains the client via `ctxt.llm_client()`.
2. Converts the request's own `ChatMessage` models into the
   `ChatCompletionMessageParam` shape the OpenAI SDK expects (via
   `ChatMessage.to_openai_param()`).
3. Calls `client.chat.completions.create(...)` and turns the response
   into this module's `LlmResult` model.
"""

from typing import TYPE_CHECKING, Any, Literal, cast

from pydantic import BaseModel, Field

from ivcap_service import DEFAULT_LLM_MODEL, JobContext, getLogger

if TYPE_CHECKING:
    import openai
    from openai.types.chat import ChatCompletionMessageParam

logger = getLogger("app")

# The roles accepted by the OpenAI chat completion API (subset of
# `ChatCompletionMessageParam`'s per-role `Literal["..."]` requirement).
ChatRole = Literal["developer", "system", "user", "assistant", "tool", "function"]


class ChatMessage(BaseModel):
    content: str = Field(..., description="The content of this message.")
    role: ChatRole = Field(..., description="The role of the messages author.")
    name: str | None = Field(
        None, description="An optional name for the participant."
    )

    def to_openai_param(self) -> "ChatCompletionMessageParam":
        """Build the `ChatCompletionMessageParam` dict expected by the OpenAI
        SDK. `ChatCompletionMessageParam` is a `Union` of per-role
        `TypedDict`s (not a class), so there is no constructor on it to
        build from - we assemble the dict ourselves instead, only
        including `name` when it is actually set (the TypedDicts are
        `total=False` and expect the key to be absent rather than `None`).
        """
        data: dict[str, Any] = {"role": self.role, "content": self.content}
        if self.name is not None:
            data["name"] = self.name
        return cast("ChatCompletionMessageParam", data)


class LlmTester(BaseModel):
    messages: list[ChatMessage] = Field(
        ..., description="A list of messages to be passed to the LLM."
    )
    model: str = Field(
        DEFAULT_LLM_MODEL, description="The LLM model to use [gpt-3.5-turbo]."
    )


class LlmResult(BaseModel):
    messages: list[dict[str, Any]] = Field(
        ...,
        description=(
            "the assistant message(s) returned for each completion choice, as "
            "returned by the LLM provider (shape depends on the model/provider)"
        ),
    )
    usage: dict[str, Any] = Field(
        ..., description="token usage statistics reported by the LLM provider"
    )


def completion(req: LlmTester, ctxt: JobContext) -> LlmResult:
    """Minimal example of calling an LLM from a worker function.

    1. Get a pre-configured client with `ctxt.llm_client()` - no need to
       worry about which provider/proxy is in use, or how it is
       authenticated; that is all handled for you based on environment
       configuration (see the module docstring above for details).
    2. Build the `messages` payload the OpenAI SDK expects. Here we reuse
       `ChatMessage.to_openai_param()` to turn our own typed request model
       into the `ChatCompletionMessageParam` dicts `create()` requires.
    3. Call `client.chat.completions.create(model=..., messages=...)` just
       like you would with the plain `openai` SDK.
    4. Translate the response into this service's own `LlmResult` model.

    Any exception raised by the client (e.g. network/auth errors, invalid
    model name) is logged and re-raised so the job is reported as failed.
    """
    try:
        client: openai.OpenAI = ctxt.llm_client()
        messages = [m.to_openai_param() for m in req.messages]
        response = client.chat.completions.create(
            model=req.model, messages=messages
        )
        return format_llm_response(response)
    except Exception as ex:
        logger.warning(f"llm execution failed - {ex}")
        raise ex


def format_llm_response(response) -> LlmResult:
    messages = [c.message.model_dump() for c in response.choices]
    usage = response.usage.model_dump()
    return LlmResult(messages=messages, usage=usage)
