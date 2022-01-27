"""
Test test_helpers.
"""
# pylint: disable=redefined-outer-name
import logging

import pytest
from shellfoundry_traffic.test_helpers import TestHelpers, create_session_from_config

from cloudshell.api.cloudshell_api import CloudShellAPISession

from helpers import get_reservation_id
from rest_api_helpers import SandboxAttachments

RESERVATION_NAME = "testing 1 2 3"


logger = logging.getLogger()
logger.setLevel(logging.DEBUG)


@pytest.fixture()
def session() -> CloudShellAPISession:
    """Yields CloudShell session."""
    session = create_session_from_config()
    yield session
    # todo: delete session.


@pytest.fixture()
def test_helper(session: CloudShellAPISession) -> TestHelpers:
    """Yields configured TestHelper object."""
    return TestHelpers(session)


def test_sandbox_attachments(test_helper: TestHelpers) -> None:
    """Test sandbox_attachments."""
    test_helper.create_reservation(RESERVATION_NAME)
    quali_api = SandboxAttachments(test_helper.session.host, test_helper.session.token_id, logging.getLogger())
    quali_api.login()
    reservation_id = get_reservation_id(test_helper.reservation)
    quali_api.attach_new_file(reservation_id, "Hello World 1", "test1.txt")
    quali_api.attach_new_file(reservation_id, "Hello World 2", "test2.txt")
    attached_files = quali_api.get_attached_files(reservation_id)
    assert "test1.txt" in attached_files
    assert "test2.txt" in attached_files
    test1_content = quali_api.get_attached_file(reservation_id, "test1.txt")
    assert test1_content.decode() == "Hello World 1"
    test2_content = quali_api.get_attached_file(reservation_id, "test2.txt")
    assert test2_content.decode() == "Hello World 2"
