from typing import Any, Dict

from fastapi.encoders import jsonable_encoder

from mlflow.gateway.config import CustomConfig, RouteConfig
from mlflow.gateway.providers.base import BaseProvider
from mlflow.gateway.providers.utils import send_request
from mlflow.gateway.schemas import completions, embeddings


class CustomProvider(BaseProvider):
    NAME = "Custom"

    def __init__(self, config: RouteConfig) -> None:
        super().__init__(config)
        if config.model.config is None or not isinstance(config.model.config, CustomConfig):
            raise TypeError(f"Unexpected config type {config.model.config}")
        self.endpoint_config: CustomConfig = config.model.config

    async def _request(self, path: str, payload: Dict[str, Any]) -> Dict[str, Any]:
        headers = {}
        if self.endpoint_config.custom_api_key is not None:
            headers["Authorization"] = f"Bearer {self.endpoint_config.custom_api_key}"
        return await send_request(
            headers=headers,
            base_url=self.endpoint_config.custom_api_key,
            path=path,
            payload=payload,
        )

    async def completions(self, payload: completions.RequestPayload) -> completions.ResponsePayload:
        payload = jsonable_encoder(payload, exclude_none=True)
        self.check_for_model_field(payload)
        resp = await self._request("completions", payload)
        return completions.ResponsePayload(
            id=resp.get("id"),
            object="text_completion",
            created=resp["created"],
            model=resp["model"],
            choices=[
                completions.Choice(
                    index=c.get("index", idx),
                    text=c["text"],
                    finish_reason=c["finish_reason"],
                )
                for idx, c in enumerate(resp["choices"])
            ],
            usage=completions.CompletionsUsage(
                prompt_tokens=resp["usage"]["prompt_tokens"],
                completion_tokens=resp["usage"]["completion_tokens"],
                total_tokens=resp["usage"]["total_tokens"],
            ),
        )

    # async def embeddings(self, payload: embeddings.RequestPayload) -> embeddings.ResponsePayload:
    #     payload = jsonable_encoder(payload, exclude_none=True)
    #     self.check_for_model_field(payload)
    #     resp = await self._request(
    #         "embed",
    #         {
    #             "model": self.config.model.name,
    #             **CohereAdapter.embeddings_to_model(payload, self.config),
    #         },
    #     )
    #     return CohereAdapter.model_to_embeddings(resp, self.config)
