import asyncio
from typing import Dict
from enum import Enum

import requests
from requests.exceptions import HTTPError, ChunkedEncodingError
from urllib3.exceptions import InvalidChunkLength

from framework.core.env_loader import BACKEND_URL, BOT_API_KEY
from framework.core.exception import AppException
from framework.core.logger import get_logger, LoggerWrapper


logger:LoggerWrapper = get_logger(__name__)


class ParamBuilder:

    def __init__(self):
        self.params = {}

    def _convert_list(self, value):
        return [str(item) for item in value]

    def add_param(self, key, value):
        if value:
            if isinstance(value, list):
                self.params[key] = self._convert_list(value)
            else:
                self.params[key] = str(value)
        return self
    
    def build(self):
        params = self.params
        self.params = {}
        return params
    

class RequestType(Enum):
    GET = "GET"
    POST = "POST"
    PUT = "PUT"
    DELETE = "DELETE"
    PATCH = "PATCH"
    OPTIONS = "OPTIONS"
    HEAD = "HEAD"


class Endpoint(Enum):
    pass


class ServiceResponse:

    def __init__(self, status_code: int, data: dict, content: bytes):
        self.status_code = status_code
        self.data = data
        self.content = content


class ServiceException(AppException):

    def __init__(self, response: requests.Response):
        
        try:
            response_body = response.json()
        except Exception:
            response_body = None

        dev_msg = ""
        usr_msg = ""

        if response_body:
            if "devMessage" in response_body and "userMessage" in response_body:
                dev_msg = response_body["devMessage"]
                usr_msg = response_body["userMessage"]
            else:
                dev_msg = f"Unknown error occured: {response_body}"
                usr_msg = "An unknown error has occured (check log for more information)."
        else:
            dev_msg = f"Unknown error occured: {response.text}" 
            usr_msg = "An unknown error has occured (check log for more information)."
        
        self.status_code = response.status_code

        super().__init__(dev_msg, usr_msg)


class ServiceClient:

    def _param_builder(self) -> ParamBuilder:
        return ParamBuilder()

    def _get_url(self, endpoint: Endpoint):
        return BACKEND_URL + endpoint.value

    def _make_request(
            self, request_type: RequestType, url: str, 
            headers: Dict, params: Dict = None, 
            body: Dict = None, retries: int = 5
            ) -> requests.Response:
        
        response = None

        for attempt in range(1, retries + 1):

            logger.debug(f"{request_type.value} {url} params={params}, body={body}")

            try:
                
                response = requests.request(method=request_type.value, url=url, headers=headers, params=params, json=body)
                response.raise_for_status()
                return response

            except HTTPError as e:
                
                if response is not None:
                    raise ServiceException(response) 
                else:
                    raise AppException(f"Could not make requests: {e}", "This service is not available, try again later.")

            except (ChunkedEncodingError, InvalidChunkLength) as e:

                logger.warning(f"ChunkedEncodingError in attempt {attempt}/{retries}: {e}")

                if attempt == retries:
                    raise AppException(
                        f"Could not make request after {attempt} attempts: {e}", 
                        "This service is not available, try again later."
                        )

            except requests.exceptions.RequestException as e:
            
                raise AppException(f"Could not make requests: {e}", "This service is not available, try again later.")
        

    async def send_request(self, request_type: RequestType, endpoint: Endpoint, params: Dict = None, body: Dict = None) -> requests.Response:
        headers = {"X-API-KEY": BOT_API_KEY}
        return await asyncio.to_thread(self._make_request, request_type, self._get_url(endpoint), headers, params, body)
    