import os
import pathlib
import shlex
import sys
import textwrap
import importlib.metadata
import importlib
import types
from typing import Optional, Union, Any

from fastapi import FastAPI, Response
from fastapi.staticfiles import StaticFiles

from mlflow.exceptions import MlflowException
from mlflow.server import handlers
from mlflow.server.handlers import (
    get_artifact_handler,
    get_metric_history_bulk_handler,
    STATIC_PREFIX_ENV_VAR,
    _add_static_prefix,
    get_model_version_artifact_handler,
    search_datasets_handler,
)
from mlflow.utils.process import _exec_cmd
from mlflow.utils.os import is_windows
from mlflow.version import VERSION

from starlette.middleware import Middleware
from starlette.requests import Request, HTTPConnection
from starlette.responses import guess_type

from starlette_context import plugins
from starlette_context.middleware import RawContextMiddleware


# NB: These are internal environment variables used for communication between
# the cli and the forked gunicorn processes.
BACKEND_STORE_URI_ENV_VAR = "_MLFLOW_SERVER_FILE_STORE"
REGISTRY_STORE_URI_ENV_VAR = "_MLFLOW_SERVER_REGISTRY_STORE"
ARTIFACT_ROOT_ENV_VAR = "_MLFLOW_SERVER_ARTIFACT_ROOT"
ARTIFACTS_DESTINATION_ENV_VAR = "_MLFLOW_SERVER_ARTIFACT_DESTINATION"
PROMETHEUS_EXPORTER_ENV_VAR = "prometheus_multiproc_dir"
SERVE_ARTIFACTS_ENV_VAR = "_MLFLOW_SERVER_SERVE_ARTIFACTS"
ARTIFACTS_ONLY_ENV_VAR = "_MLFLOW_SERVER_ARTIFACTS_ONLY"

REL_STATIC_FOLDER = "js/build"
STATIC_FOLDER = str((pathlib.Path(__file__).parent / REL_STATIC_FOLDER).resolve())


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
app = FastAPI(middleware=middleware)
app.mount("/" + REL_STATIC_FOLDER, StaticFiles(directory=STATIC_FOLDER), name="static")


for http_path, handler, methods in handlers.get_endpoints():
    app.add_api_route(http_path, handler, methods=methods)

if os.getenv(PROMETHEUS_EXPORTER_ENV_VAR):
    from mlflow.server.prometheus_exporter import activate_prometheus_exporter

    prometheus_metrics_path = os.getenv(PROMETHEUS_EXPORTER_ENV_VAR)
    if not os.path.exists(prometheus_metrics_path):
        os.makedirs(prometheus_metrics_path)
    activate_prometheus_exporter(app)


# Provide a health check endpoint to ensure the application is responsive
@app.get("/health")
def health():
    return "OK", 200


# Provide an endpoint to query the version of mlflow running on the server
@app.get("/version")
def version():
    return VERSION, 200


# Serve the "get-artifact" route.
@app.get(_add_static_prefix("/get-artifact"))
def serve_artifacts():
    return get_artifact_handler()


# Serve the "model-versions/get-artifact" route.
@app.get(_add_static_prefix("/model-versions/get-artifact"))
def serve_model_version_artifact():
    return get_model_version_artifact_handler()


# Serve the "metrics/get-history-bulk" route.
@app.get(_add_static_prefix("/ajax-api/2.0/mlflow/metrics/get-history-bulk"))
def serve_get_metric_history_bulk():
    return get_metric_history_bulk_handler()


# Serve the "experiments/search-datasets" route.
@app.get(_add_static_prefix("/ajax-api/2.0/mlflow/experiments/search-datasets"))
def serve_search_datasets():
    return search_datasets_handler()


# We expect the react app to be built assuming it is hosted at /static-files, so that requests for
# CSS/JS resources will be made to e.g. /static-files/main.css and we can handle them here.
# The files are hashed based on source code, so ok to send Cache-Control headers via max_age.
@app.get(_add_static_prefix("/static-files/{path:path}"))
def serve_static_file(path):
    return _send_from_directory(STATIC_FOLDER, path)


def _send_from_directory(
    directory: Union[os.PathLike, str],
    path: Union[os.PathLike, str],
):
    if ".." in path:
        return None
    path = os.path.join(directory, path)
    with open(path, "rb") as f:
        data = f.read()
    mimetype, _ = guess_type(path)
    return Response(content=data, media_type=mimetype)


# Serve the index.html for the React App for all other routes.
@app.get(_add_static_prefix("/"))
def serve():
    if os.path.exists(os.path.join(STATIC_FOLDER, "index.html")):
        return _send_from_directory(STATIC_FOLDER, "index.html")

    text = textwrap.dedent(
        """
    Unable to display MLflow UI - landing page (index.html) not found.

    You are very likely running the MLflow server using a source installation of the Python MLflow
    package.

    If you are a developer making MLflow source code changes and intentionally running a source
    installation of MLflow, you can view the UI by running the Javascript dev server:
    https://github.com/mlflow/mlflow/blob/master/CONTRIBUTING.md#running-the-javascript-dev-server

    Otherwise, uninstall MLflow via 'pip uninstall mlflow', reinstall an official MLflow release
    from PyPI via 'pip install mlflow', and rerun the MLflow server.
    """
    )
    return Response(text, media_type="text/plain")


def _find_app(app_name: str) -> str:
    apps = importlib.metadata.entry_points().get("mlflow.app", [])
    for app in apps:
        if app.name == app_name:
            return app.value

    raise MlflowException(
        f"Failed to find app '{app_name}'. Available apps: {[a.name for a in apps]}"
    )


def _is_factory(app: str) -> bool:
    """
    Returns True if the given app is a factory function, False otherwise.

    :param app: The app to check, e.g. "mlflow.server.app:app"
    """
    module, obj_name = app.rsplit(":", 1)
    mod = importlib.import_module(module)
    obj = getattr(mod, obj_name)
    return isinstance(obj, types.FunctionType)


def get_app_client(app_name: str, *args, **kwargs):
    """
    Instantiate a client provided by an app.

    :param app_name: The app name defined in `setup.py`, e.g., "basic-auth".
    :param args: Additional arguments passed to the app client constructor.
    :param kwargs: Additional keyword arguments passed to the app client constructor.
    :return: An app client instance.
    """
    clients = importlib.metadata.entry_points().get("mlflow.app.client", [])
    for client in clients:
        if client.name == app_name:
            cls = client.load()
            return cls(*args, **kwargs)

    raise MlflowException(
        f"Failed to find client for '{app_name}'. Available clients: {[c.name for c in clients]}"
    )


def _build_waitress_command(waitress_opts, host, port, app_name, is_factory):
    opts = shlex.split(waitress_opts) if waitress_opts else []
    return [
        "uvicorn",
        *opts,
        f"--host={host}",
        f"--port={port}",
        "mlflow.server:app",
    ]


def _build_gunicorn_command(gunicorn_opts, host, port, workers, app_name):
    bind_address = f"{host}:{port}"
    opts = shlex.split(gunicorn_opts) if gunicorn_opts else []
    return [
        "gunicorn",
        *opts,
        "-b",
        bind_address,
        "-w",
        str(workers),
        app_name,
    ]


def _run_server(
    file_store_path,
    registry_store_uri,
    default_artifact_root,
    serve_artifacts,
    artifacts_only,
    artifacts_destination,
    host,
    port,
    static_prefix=None,
    workers=None,
    gunicorn_opts=None,
    waitress_opts=None,
    expose_prometheus=None,
    app_name=None,
):
    """
    Run the MLflow server, wrapping it in gunicorn or waitress on windows
    :param static_prefix: If set, the index.html asset will be served from the path static_prefix.
                          If left None, the index.html asset will be served from the root path.
    :return: None
    """
    env_map = {}
    if file_store_path:
        env_map[BACKEND_STORE_URI_ENV_VAR] = file_store_path
    if registry_store_uri:
        env_map[REGISTRY_STORE_URI_ENV_VAR] = registry_store_uri
    if default_artifact_root:
        env_map[ARTIFACT_ROOT_ENV_VAR] = default_artifact_root
    if serve_artifacts:
        env_map[SERVE_ARTIFACTS_ENV_VAR] = "true"
    if artifacts_only:
        env_map[ARTIFACTS_ONLY_ENV_VAR] = "true"
    if artifacts_destination:
        env_map[ARTIFACTS_DESTINATION_ENV_VAR] = artifacts_destination
    if static_prefix:
        env_map[STATIC_PREFIX_ENV_VAR] = static_prefix

    if expose_prometheus:
        env_map[PROMETHEUS_EXPORTER_ENV_VAR] = expose_prometheus

    if app_name is None:
        app = f"{__name__}:app"
        is_factory = False
    else:
        app = _find_app(app_name)
        is_factory = _is_factory(app)
        # `waitress` doesn't support `()` syntax for factory functions.
        # Instead, we need to use the `--call` flag.
        app = f"{app}()" if (not is_windows() and is_factory) else app

    # TODO: eventually may want waitress on non-win32
    if sys.platform == "win32":
        full_command = _build_waitress_command(waitress_opts, host, port, app, is_factory)
    else:
        full_command = _build_gunicorn_command(gunicorn_opts, host, port, workers or 4, app)
    _exec_cmd(full_command, extra_env=env_map, capture_output=False)
