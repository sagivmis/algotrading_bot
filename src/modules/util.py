import logging
import typing
import requests


logger = logging.getLogger()


class Request:
    def __init__(self, base_url, headers) -> None:
        self.base_url = base_url
        self.headers = headers

    def raise_error(
        self, method: str, type: str, endpoint: str, data: typing.Dict, e=None
    ):
        logger.error(
            f"{type.capitalize()}Error: Error while executing {method} request to {self.base_url + endpoint}.\n{data} was provided.\nMessage: {e}"
        )

    def GET(self, endpoint: str, data: typing.Dict):
        try:
            response = requests.get(
                self.base_url + endpoint, params=data, headers=self.headers
            )
            if response.status_code == 200:
                return response.json()
            else:
                self.raise_error("GET", "status", endpoint, data)
        except Exception as e:
            self.raise_error("GET", "connection", endpoint, data, e)
            return None

    def POST(self, endpoint: str, data: typing.Dict):
        try:
            response = requests.post(
                self.base_url + endpoint, data=data, headers=self.headers
            )
            if response.status_code == 200:
                return response.json()
            else:
                self.raise_error("POST", "status", endpoint, data)
        except Exception as e:
            self.raise_error("GET", "connection", endpoint, data, e)
            return None

    def DELETE(self, endpoint: str, data: typing.Dict):
        try:
            response = requests.delete(
                self.base_url + endpoint, data=data, headers=self.headers
            )
            if response.status_code == 200:
                return response.json()
            else:
                self.raise_error("DELETE", "status", endpoint, data)
        except Exception as e:
            self.raise_error("GET", "connection", endpoint, data, e)
            return None
