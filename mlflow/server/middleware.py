import base64
import binascii

from starlette.authentication import AuthenticationError
from starlette.middleware import Middleware
from starlette.requests import Request, HTTPConnection
from starlette_context import plugins
from starlette_context.middleware import RawContextMiddleware
from typing import Optional, Union, Any


class QueryParamsPlugin(plugins.base.Plugin):
    key = "query_params"

    async def process_request(
        self, request: Union[Request, HTTPConnection]
    ) -> Optional[Any]:
        assert isinstance(self.key, str)
        return request.query_params


class BodyPlugin(plugins.base.Plugin):
    key = "body"

    async def process_request(
        self, request: Union[Request, HTTPConnection]
    ) -> Optional[Any]:
        assert isinstance(self.key, str)
        if hasattr(request, "body"):
            return await request.body()
        return None


class MethodPlugin(plugins.base.Plugin):
    key = "method"

    async def process_request(
        self, request: Union[Request, HTTPConnection]
    ) -> Optional[Any]:
        assert isinstance(self.key, str)
        return request.method


class PathPlugin(plugins.base.Plugin):
    key = "path"

    async def process_request(
        self, request: Union[Request, HTTPConnection]
    ) -> Optional[Any]:
        assert isinstance(self.key, str)
        return request.scope["path"]


class AuthorizationPlugin(plugins.base.Plugin):
    key = "authorization"

    async def process_request(
        self, request: Union[Request, HTTPConnection]
    ) -> Optional[Any]:
        assert isinstance(self.key, str)
        if auth := request.headers.get("authorization"):
            try:
                scheme, credentials = auth.split()
                if scheme.lower() != "basic":
                    return
                decoded = base64.b64decode(credentials).decode("ascii")
            except (ValueError, UnicodeDecodeError, binascii.Error):
                raise AuthenticationError("Invalid basic auth credentials")

            username, _, password = decoded.partition(":")
            return {
                "username": username,
                "password": password,
            }


class RequestContextMiddleware(RawContextMiddleware):
    @staticmethod
    def get_request_object(
        scope, receive, send
    ) -> Union[Request, HTTPConnection]:
        return Request(scope, receive, send)


middleware = [
    Middleware(
        RequestContextMiddleware,
        plugins=(
            QueryParamsPlugin(),
            BodyPlugin(),
            MethodPlugin(),
            PathPlugin(),
            AuthorizationPlugin(),
        )
    )
]
