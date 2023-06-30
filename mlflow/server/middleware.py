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
        )
    )
]
