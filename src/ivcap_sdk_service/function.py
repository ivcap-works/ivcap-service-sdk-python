
from argparse import ArgumentError, ArgumentParser
import os
import sys
from logging import Logger
from typing import Any, Callable, ClassVar, Generic, Type as TypeT, TypeVar, Union, Optional, Sequence
from typing_extensions import Self
from pydantic import Field, PrivateAttr, field_serializer, model_validator
from argparse import ArgumentError

from .cio.io_adapter import IOReadable, IOWritable, OnCloseF, QueueMessage
from .aspect import Aspect
from .service import BaseService, Type, BaseParameter
from .itypes import URN, ServiceArgs, SupportedMimeTypes
from .ivcap import get_config
from .utils import get_banner
from .logger import logger, sys_logger
from .config import Config, Command

DEF_INPUT_PARAM_NAME = "input"
DEF_OUTPUT_PARAM_NAME = "output"

class FunctionInParameter(BaseParameter):
    SCHEMA: str = None

    def __init__(self, **args):
        super().__init__(type=Type.QUEUE, name=DEF_INPUT_PARAM_NAME, optional=True, **args)

class FunctionArtifactInParameter(FunctionInParameter):
    mimeType: str = None

class FunctionOutParameter(BaseParameter):
    SCHEMA: str = None

    def __init__(self, **args):
        super().__init__(type=Type.QUEUE, name=DEF_OUTPUT_PARAM_NAME, optional=True, **args)

class FunctionRequest(Aspect):
    pass

# class ArtifactFunctionRequestConstraint(BaseModel):
#     parameterName: str = Field(None, title="parameter-name", description="optional name of input parameter")
#     requiredMimeType: str = Field(None, title="required-mime-type", description="optional constraint on artifact mime-type")

class ArtifactFunctionRequest(FunctionRequest):
    SCHEMA: ClassVar[str] = 'urn:ivcap:schema:artifact-function-request.1'
    TITLE: ClassVar[str] = "Artifact Function Request"
    DESCRIPTION: ClassVar[str] = "Contains the URN of an artifact being the input to a function"

    # CONSTRAINTS: ClassVar[ArtifactFunctionRequestConstraint] = None

    artifactURN: URN = Field(description="URN to artifact to process", title="artifact-urn")
    _readable: IOReadable = PrivateAttr("")

    @property
    def readable(self) -> IOReadable:
        return self._readable


class FunctionResponse(Aspect):
    pass

class ArtifactFunctionResponse:
    name: str
    data_or_lambda: Union[Any, Callable[[IOWritable], None]]
    mime_type: Union[str, SupportedMimeTypes]
    metadata: Optional[Union[Aspect, Sequence[Aspect]]] = None,
    seekable: Optional[bool]=False,
    is_binary: Optional[bool]=None,
    on_close: Optional[OnCloseF] = None

    def __init__(
        self,
        name: str,
        data_or_lambda: Union[Any, Callable[[IOWritable], None]],
        mime_type: Union[str, SupportedMimeTypes],
        *,
        metadata: Optional[Union[Aspect, Sequence[Aspect]]] = None,
        seekable=False,
        is_binary: Optional[bool]=None,
        on_close: Optional[OnCloseF] = None
    ):
        self.name = name
        self.data_or_lambda = data_or_lambda
        self.mime_type = mime_type
        self.metadata = metadata
        self.seekable = seekable
        self.is_binary = is_binary
        self.on_close = on_close

T = TypeVar('T', bound=FunctionRequest)
U = TypeVar('U', bound=FunctionResponse)

class FunctionExecError(Exception):
    def __init__(self, message, ex=None):
        super().__init__(message)
        self.ex = ex

class FunctionService(BaseService, Generic[T, U]):
    request: TypeT[T] = Field(description="dataclass describing shape of request")
    response: TypeT[U] = Field(description="dataclass describing shape of response")

    _input: FunctionInParameter = PrivateAttr()
    _output: FunctionOutParameter = PrivateAttr(None)
    _service_url: str = PrivateAttr(None)

    @field_serializer("request", return_type=dict)
    @staticmethod
    def serialize_request(request: TypeT[T]) -> dict:
        return request.json_schema()

    @field_serializer("response", return_type=dict)
    @staticmethod
    def serialize_response(response: TypeT[U]) -> dict:
        return response.json_schema() # "response"

    @model_validator(mode='after')
    def check_parameters(self) -> Self:
        pia = list(filter(lambda p: isinstance(p, FunctionInParameter), self.parameters))
        if len(pia) == 0:
            schema = self.request.schema()
            self._input = FunctionInParameter(SCHEMA=schema)
            self.parameters.append(self._input)
        elif len(pia) == 1:
            self._input = pia[0]
        else:
            raise ArgumentError("Only one INPUT function parameter allowed")

        if self.response:
            poa = list(filter(lambda p: isinstance(p, FunctionOutParameter), self.parameters))
            if len(poa) == 0:
                schema = self.response.schema()
                self._output = FunctionOutParameter(SCHEMA=schema)
                self.parameters.append(self._output)
            elif len(pia) == 1:
                self._output = poa[0]
            else:
                raise ArgumentError("Only one OUTPUT function parameter allowed")
        return self

    # SERVICE_URL: str
#        self.SERVICE_URL = args.pop('ivcap:service_url', None)
#    service_url_def = os.getenv('IVCAP_SERVICE_URL')

    def _append_sys_arguments(self, ap: ArgumentParser) -> ArgumentParser:
        url = os.getenv('IVCAP_SERVICE_URL')
        ap.add_argument("--ivcap:service-url", metavar="URL",
            help=f"Run service as http server [IVCAP_SERVICE_URL={url}]")
        return super()._append_sys_arguments(ap)

    def _get_command(self, cfg: Config) -> Optional[Command]:
        """Return the command to execute or None if it has been taken care of
        """
        self._service_url = cfg.CUSTOM_ARGS.get("ivcap:service_url")
        return super()._get_command(cfg)

    def run(self, handler: Callable[[ServiceArgs, Logger], Callable[[T], U]]):
        def h(args):
            nonlocal handler

            f = handler(args, logger)
            if self._service_url:
                return self._run_as_server(f)
            else:
                self._run_queue(args, f)

        self._run(h)

    def _run_queue(self, args, f):
        in_q = getattr(args, self._input.name)
        if not in_q:
            raise Exception(f"Missing '--{self._input.name}' declaration")
        out_q = getattr(args, self._output.name)
        for r in in_q:
            try:
                req = self._to_request(r)
                res = self._run_one(req, f)
                if res:
                    if out_q:
                        out_q.push(QueueMessage.from_aspect(res))
                    else:
                        sys_logger.warning(f"do not know what to do with result - {res}")
            except FunctionExecError as fex:
                sys_logger.warning(f"error '{fex.message}' while processing '{r}' - {fex.ex}")
                sys.exit(-1)
            except Exception as ex:
                sys_logger.warning(f"unexpected error while processing '{r}' - {ex}")
                sys.exit(-1)

    def _run_one(self, req, f) -> FunctionResponse:
        try:
            res = f(req)
        except Exception as ex:
            raise FunctionExecError("while executing map function", ex)

        if not isinstance(res, self.response):
            raise FunctionExecError(f"unexpect response type. Expected '{self.response}', but got '{type(res)}'")
        if not isinstance(res, Aspect):
            raise FunctionExecError(f"unexpect response type. Expected 'Aspect', but got '{type(res)}'")

        return res

    def _to_request(self, r, mime_type=None) -> FunctionRequest:
        isArtifactReq = issubclass(self.request, ArtifactFunctionRequest)

        if isArtifactReq:
            if isinstance(r, IOReadable):
                req = ArtifactFunctionRequest(artifactURN=r.urn)
                req._readable = r
                return req
            ## check if it is beoing passed in as http body
            raise FunctionExecError("cannot convert to 'ArtifactFunctionRequest'")

        try:
            if isinstance(r, dict):
                r = QueueMessage.from_dict(r)
            if isinstance(r, QueueMessage):
                req = self.request(**r.content)
        except Exception as ex:
            raise FunctionExecError("while parsing request", ex)
        return req

    def _run_as_server(self, f):
        from fastapi import FastAPI, Request, Response, HTTPException
        import uvicorn
        from urllib.parse import urlparse
        import json

        url = urlparse(self._service_url)

        app = FastAPI(
            title=self.title,
            description=self.description,
            version=get_banner(self),
            contact=self.contact.dict() if self.contact else None,
            license_info=self.license_info.dict() if self.license_info else None,
            docs_url="/api",
            root_path=os.environ.get("IVCAP_ROOT_PATH", "")
        )

        @app.post("/")
        async def service(req: Request):
            body = await req.body()
            ct = req.headers['content-type']
            try:
                if ct == "application/json":
                    bs = body.decode('utf-8')
                    data = json.loads(bs)
                    req = self._to_request(data, ct)
                    resp = self._run_one(req, f)
                    return Response(content=resp.dump_json(), media_type="application/json")
            except Exception as ex:
                raise HTTPException(status_code=500, detail=ex.args)
        # Allows platform to check if everything is OK
        @app.get("/_healtz")
        def healtz():
            return get_banner(self)

        uvicorn.run(app, host=url.hostname, port=url.port)