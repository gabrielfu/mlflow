from typing import Type, Union

from mlflow.exceptions import MlflowException
from mlflow.gateway.config import Provider
from mlflow.gateway.plugins import import_plugin_obj, string_is_plugin_obj
from mlflow.gateway.providers.base import BaseProvider


def get_provider(provider: Union[str, Provider]) -> Type[BaseProvider]:
    from mlflow.gateway.providers.ai21labs import AI21LabsProvider
    from mlflow.gateway.providers.anthropic import AnthropicProvider
    from mlflow.gateway.providers.bedrock import AmazonBedrockProvider
    from mlflow.gateway.providers.cohere import CohereProvider
    from mlflow.gateway.providers.huggingface import HFTextGenerationInferenceServerProvider
    from mlflow.gateway.providers.mistral import MistralProvider
    from mlflow.gateway.providers.mlflow import MlflowModelServingProvider
    from mlflow.gateway.providers.mosaicml import MosaicMLProvider
    from mlflow.gateway.providers.openai import OpenAIProvider
    from mlflow.gateway.providers.palm import PaLMProvider
    from mlflow.gateway.providers.togetherai import TogetherAIProvider

    provider_to_class = {
        Provider.OPENAI: OpenAIProvider,
        Provider.ANTHROPIC: AnthropicProvider,
        Provider.COHERE: CohereProvider,
        Provider.AI21LABS: AI21LabsProvider,
        Provider.MOSAICML: MosaicMLProvider,
        Provider.PALM: PaLMProvider,
        Provider.MLFLOW_MODEL_SERVING: MlflowModelServingProvider,
        Provider.HUGGINGFACE_TEXT_GENERATION_INFERENCE: HFTextGenerationInferenceServerProvider,
        Provider.BEDROCK: AmazonBedrockProvider,
        Provider.MISTRAL: MistralProvider,
        Provider.TOGETHERAI: TogetherAIProvider,
    }
    if prov := provider_to_class.get(provider):
        return prov

    if isinstance(provider, str) and string_is_plugin_obj(provider):
        prov = import_plugin_obj(provider)
        if not (isinstance(prov, type) and issubclass(prov, BaseProvider)):
            raise MlflowException.invalid_parameter_value(
                f"Plugin provider {provider} is not a subclass of BaseProvider"
            )
        return prov

    raise MlflowException.invalid_parameter_value(f"Provider {provider} not found")
