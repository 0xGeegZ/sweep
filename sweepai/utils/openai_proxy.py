import baserun
import random
import os

import openai
from loguru import logger

from sweepai.config.server import (
    AZURE_API_KEY,
    BASERUN_API_KEY,
    MULTI_REGION_CONFIG,
    OPENAI_API_BASE,
    OPENAI_API_ENGINE_GPT4,
    OPENAI_API_ENGINE_GPT4_32K,
    OPENAI_API_ENGINE_GPT35,
    OPENAI_API_KEY,
    OPENAI_API_TYPE,
    OPENAI_API_VERSION,
)
from sweepai.logn import file_cache

class OpenAIProxy:
    def __init__(self):
        pass

    @file_cache(ignore_params=[])
    @baserun.trace
    def call_openai(self, model, messages, max_tokens, temperature) -> str:
        try:
            engine = None
            if (
                model == "gpt-3.5-turbo-16k"
                or model == "gpt-3.5-turbo-16k"
                and OPENAI_API_ENGINE_GPT35 is not None
            ):
                engine = OPENAI_API_ENGINE_GPT35
            elif (
                model == "gpt-4"
                or model == "gpt-4"
                and OPENAI_API_ENGINE_GPT4 is not None
            ):
                engine = OPENAI_API_ENGINE_GPT4
            elif (
                model == "gpt-4-32k"
                or model == "gpt-4-32k"
                and OPENAI_API_ENGINE_GPT4_32K is not None
            ):
                engine = OPENAI_API_ENGINE_GPT4_32K
            if OPENAI_API_TYPE is None or engine is None:
                # openai.api_key = OPENAI_API_KEY
                # openai.api_base = "https://api.openai.com/v1"
                openai.api_base = "https://openrouter.ai/api/v1"
                openai.api_key = os.getenv("OPENROUTER_API_KEY")
                openai.api_version = None
                openai.api_type = "open_ai"
                logger.info(f"Calling {model} on OpenAI.")
                response = openai.ChatCompletion.create(
                    # model=model,
                    model="openai/" + model,
                    messages=messages,
                    max_tokens=max_tokens,
                    temperature=temperature,
                    headers= {
                        "HTTP-Referer": os.getenv("YOUR_SITE_URL"),  # Added comma here
                        "X-Title": os.getenv("YOUR_APP_NAME")
                    }
                )
                return response["choices"][0].message.content
            # validity checks for MULTI_REGION_CONFIG
            if (
                MULTI_REGION_CONFIG is None
                or not isinstance(MULTI_REGION_CONFIG, list)
                or len(MULTI_REGION_CONFIG) == 0
                or not isinstance(MULTI_REGION_CONFIG[0], list)
            ):
                logger.info(
                    f"Calling {model} with engine {engine} on Azure url {OPENAI_API_BASE}."
                )
                openai.api_type = OPENAI_API_TYPE
                openai.api_base = OPENAI_API_BASE
                openai.api_version = OPENAI_API_VERSION
                openai.api_key = AZURE_API_KEY
                response = openai.ChatCompletion.create(
                    engine=engine,
                    model=model,
                    messages=messages,
                    max_tokens=max_tokens,
                    temperature=temperature,
                )
                return response["choices"][0].message.content
            # multi region config is a list of tuples of (region_url, api_key)
            # we will try each region in order until we get a response
            # randomize the order of the list
            SHUFFLED_MULTI_REGION_CONFIG = random.sample(
                MULTI_REGION_CONFIG, len(MULTI_REGION_CONFIG)
            )
            for region_url, api_key in SHUFFLED_MULTI_REGION_CONFIG:
                try:
                    logger.info(
                        f"Calling {model} with engine {engine} on Azure url {region_url}."
                    )
                    openai.api_key = api_key
                    openai.api_base = region_url
                    openai.api_version = OPENAI_API_VERSION
                    openai.api_type = OPENAI_API_TYPE
                    response = openai.ChatCompletion.create(
                        engine=engine,
                        model=model,
                        messages=messages,
                        max_tokens=max_tokens,
                        temperature=temperature,
                    )
                    return response["choices"][0].message.content
                except SystemExit:
                    raise SystemExit
                except Exception as e:
                    logger.exception(f"Error calling {region_url}: {e}")
            raise Exception("No Azure regions available")
        except SystemExit:
            raise SystemExit
        except Exception as e:
            if OPENAI_API_KEY:
                try:
                    # openai.api_key = OPENAI_API_KEY
                    # openai.api_base = "https://api.openai.com/v1"
                    openai.api_base = "https://openrouter.ai/api/v1"
                    openai.api_key = os.getenv("OPENROUTER_API_KEY")
                    openai.api_version = None
                    openai.api_type = "open_ai"
                    logger.info(f"Calling {model} with OpenAI.")
                    response = openai.ChatCompletion.create(
                        # model=model,
                        model="openai/" + model,
                        messages=messages,
                        max_tokens=max_tokens,
                        temperature=temperature,
                        headers= {
                            "HTTP-Referer": os.getenv("YOUR_SITE_URL"),  # Added comma here
                            "X-Title": os.getenv("YOUR_APP_NAME")
                        }
                    )
                    return response["choices"][0].message.content
                except SystemExit:
                    raise SystemExit
                except Exception as _e:
                    logger.error(f"OpenAI API Key found but error: {_e}")
            logger.error(f"OpenAI API Key not found and Azure Error: {e}")
            # Raise exception to report error
            raise e
