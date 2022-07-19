"""
Helpers wrapping some Cloudshell REST API calls that has no official python API.
"""
import json
import logging
from io import StringIO
from json import JSONDecodeError
from typing import Union

from requests import Response, Session
from urllib3 import disable_warnings

disable_warnings()


class RestClientException(Exception):
    """Base class for REST client exceptions."""


class RestClientUnauthorizedException(RestClientException):
    """Unauthorized access exception."""


class RestJsonClient:
    """CloudShell REST client."""

    def __init__(self, host: str, use_https: bool = True) -> None:
        """Init REST session."""
        self._host = host
        self._use_https = use_https
        self.session = Session()

    def _build_url(self, uri: str) -> str:
        """Build full URI from relative URI."""
        if self._host not in uri:
            if not uri.startswith("/"):
                uri = "/" + uri
            if self._use_https:
                url = f"https://{self._host}{uri}"
            else:
                url = f"http://{self._host}{uri}"
        else:
            url = uri
        return url

    def _valid(self, response: Response) -> Response:
        """Validate response."""
        if response.status_code in [200, 201, 204]:
            try:
                content = json.loads(response.content.decode("utf-8"))
            except JSONDecodeError:
                content = response.content.decode("utf-8")
            if isinstance(content, dict) and not content["Success"]:
                raise RestClientException(self.__class__.__name__, f"fRequest failed: {content['ErrorMessage']}")
            return response
        if response.status_code in [401]:
            raise RestClientUnauthorizedException(self.__class__.__name__, "Incorrect login or password")
        raise RestClientException(self.__class__.__name__, f"fRequest failed: {response.status_code}, {response.text}")

    def request_put(self, uri: str, data: dict) -> str:
        """PUT."""
        response = self.session.put(self._build_url(uri), data, verify=False)
        return self._valid(response).json()

    def request_post(self, uri: str, data: dict) -> Union[bytes, dict]:
        """POST."""
        response = self.session.post(self._build_url(uri), json=data, verify=False)
        try:
            return self._valid(response).json()
        except JSONDecodeError:
            return self._valid(response).content

    def request_post_files(self, uri: str, data: dict, files: dict) -> dict:
        """POST files."""
        response = self.session.post(self._build_url(uri), data=data, files=files, verify=False)
        return self._valid(response).json()

    def request_get(self, uri: str) -> Response:
        """GET."""
        response = self.session.get(self._build_url(uri), verify=False)
        return self._valid(response)

    def request_delete(self, uri: str) -> bytes:
        """DELETE."""
        response = self.session.delete(self._build_url(uri), verify=False)
        return self._valid(response).content


class SandboxAttachments:
    """Cloudshell REST API wrappers to manage sandbox attachments."""

    def __init__(self, host: str, token: str, logger: logging.Logger) -> None:
        """Initialize cloudshell REST client."""
        self.host = host
        if ":" not in self.host:
            self.host += ":9000"
        self._logger = logger
        self._token = token
        self.__rest_client = RestJsonClient(self.host, False)

    def login(self) -> None:
        """Login to cloudshell."""
        uri = "API/Auth/Login"
        json_data = {"token": self._token}
        result = self.__rest_client.request_put(uri, json_data).replace('"', "")
        self.__rest_client.session.headers.update(authorization=f"Basic {result}")

    def attach_new_file(self, reservation_id: str, file_data: Union[str, StringIO], file_name: str) -> None:
        """Attach file to reservation."""
        file_to_upload = {"QualiPackage": file_data}
        data = {"reservationId": reservation_id, "saveFileAs": file_name, "overwriteIfExists": "true"}
        self.__rest_client.request_post_files("API/Package/AttachFileToReservation", data=data, files=file_to_upload)

    def get_attached_files(self, reservation_id: str) -> list:
        """Get all attached file names from reservation."""
        uri = f"API/Package/GetReservationAttachmentsDetails/{reservation_id}"
        result = self.__rest_client.request_get(uri).json()
        return result["AllAttachments"]

    def get_attached_file(self, reservation_id: str, file_name: str) -> bytes:
        """Get attached file content from reservation."""
        uri = f"API/Package/GetReservationAttachment/{reservation_id}"
        data = {"reservationId": reservation_id, "FileName": file_name, "SaveToFolderPath": r"na"}
        return self.__rest_client.request_post(uri, data)  # type: ignore[return-value]

    def remove_attached_files(self, reservation_id: str) -> None:
        """Remove all attached files from a sandbox."""
        for file_name in self.get_attached_files(reservation_id):
            file_to_delete = {"reservationId": reservation_id, "FileName": file_name}
            self.__rest_client.request_post("API/Package/DeleteFileFromReservation", data=file_to_delete)
