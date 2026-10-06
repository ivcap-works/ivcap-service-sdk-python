#
# Copyright (c) 2025 Commonwealth Scientific and Industrial Research Organisation (CSIRO). All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file. See the AUTHORS file for names of contributors.
#
"""
LLM completion worker function (used for the 'llm' section of a
'test-batch' Request).
"""

import os
from typing import Any

from pydantic import BaseModel, Field

from ivcap_service import getLogger

logger = getLogger("app")


class ChatMessage(BaseModel):
    content: str = Field(..., description="The content of this message.")
    role: str = Field(..., description="The role of the messages author.")
    name: str | None = Field(
        None, description="An optional name for the participant."
    )


class LlmTester(BaseModel):
    messages: list[ChatMessage] = Field(
        ..., description="A list of messages to be passed to the LLM."
    )
    model: str | None = Field(
        "sciansa-default", description="The LLM model to use [gpt-3.5-turbo]."
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


def completion(req: LlmTester) -> LlmResult:
    import openai

    try:
        client = create_openai_client(openai.OpenAI)
        response = client.chat.completions.create(
            model=req.model, messages=[m.model_dump() for m in req.messages]
        )
        return format_llm_response(response)
    except Exception as ex:
        logger.warning(f"llm execution failed - {ex}")
        raise ex


def format_llm_response(response) -> LlmResult:
    messages = [c.message.model_dump() for c in response.choices]
    usage = response.usage.model_dump()
    return LlmResult(messages=messages, usage=usage)


def create_openai_client(f):
    base_url = os.getenv("LITELLM_PROXY")
    if base_url is None:
        return f()
    else:
        return f(base_url=f"{base_url}/v1", api_key="not-needed")
