"""
Test test_helpers.
"""
# pylint: disable=redefined-outer-name
import logging

import pytest
from shellfoundry_traffic.test_helpers import TgTestHelpers, create_session_from_config

from cloudshell.api.cloudshell_api import CloudShellAPISession
from cloudshell.logging.qs_logger import get_qs_logger
from cloudshell.traffic.helpers import get_reservation_id
from cloudshell.traffic.rest_api_helpers import RestClientException, RestClientUnauthorizedException, SandboxAttachments

RESERVATION_NAME = "testing 1 2 3"


logger = get_qs_logger()
logger.setLevel(logging.DEBUG)


@pytest.fixture()
def session() -> CloudShellAPISession:
    """Yield CloudShell session."""
    return create_session_from_config()


@pytest.fixture()
def test_helpers(session: CloudShellAPISession) -> TgTestHelpers:
    """Yield configured TestHelper object."""
    return TgTestHelpers(session)


def test_sandbox_attachments(test_helpers: TgTestHelpers) -> None:
    """Test sandbox_attachments."""
    test_helpers.create_reservation(RESERVATION_NAME)
    quali_api = SandboxAttachments(test_helpers.session.host, test_helpers.session.token_id, logging.getLogger())
    quali_api.login()
    reservation_id = get_reservation_id(test_helpers.reservation)
    quali_api.attach_new_file(reservation_id, "Hello World 1", "test1.txt")
    quali_api.attach_new_file(reservation_id, "Hello World 2", "test2.txt")
    attached_files = quali_api.get_attached_files(reservation_id)
    assert "test1.txt" in attached_files
    assert "test2.txt" in attached_files
    test1_content = quali_api.get_attached_file(reservation_id, "test1.txt")
    assert test1_content.decode() == "Hello World 1"
    test2_content = quali_api.get_attached_file(reservation_id, "test2.txt")
    assert test2_content.decode() == "Hello World 2"
    quali_api.remove_attached_files(reservation_id)
    assert not quali_api.get_attached_files(reservation_id)


def test_negative(test_helpers: TgTestHelpers) -> None:
    """Negative tests."""
    test_helpers.create_reservation(RESERVATION_NAME)
    quali_api = SandboxAttachments(test_helpers.session.host, "Invalid", logging.getLogger())
    with pytest.raises(RestClientUnauthorizedException):
        quali_api.login()
    quali_api = SandboxAttachments(test_helpers.session.host, test_helpers.session.token_id, logging.getLogger())
    quali_api.login()
    with pytest.raises(RestClientException):
        quali_api.attach_new_file("Invalid", "Hello World 1", "test1.txt")
