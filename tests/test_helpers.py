"""
Test test_helpers.
"""
# pylint: disable=redefined-outer-name
import logging
from typing import Iterable

import pytest
from shellfoundry_traffic.test_helpers import TestHelpers, create_session_from_config

from cloudshell.api.cloudshell_api import CloudShellAPISession
from cloudshell.logging.qs_logger import get_qs_logger
from cloudshell.sandbox_rest.sandbox_api import SandboxRestApiSession
from cloudshell.traffic.helpers import ReservationOutputHandler, get_reservation_id
from cloudshell.workflow.orchestration.sandbox import Sandbox

logger = get_qs_logger()
logger.setLevel(logging.DEBUG)


REST_SERVER = "172.30.180.76"


@pytest.fixture
def session() -> CloudShellAPISession:
    """Yield CloudShell session."""
    return create_session_from_config()


@pytest.fixture
def test_helpers(session: CloudShellAPISession) -> Iterable[TestHelpers]:
    """Yield configured TestHelpers object with reservation."""
    test_helpers = TestHelpers(session)
    test_helpers.create_reservation()
    yield test_helpers
    test_helpers.end_reservation()


@pytest.fixture
def sandbox(test_helpers: TestHelpers) -> Sandbox:
    """Yield Sandbox."""
    test_helpers.attach_to_cloudshell_as()
    return Sandbox()


@pytest.fixture
def rest_api(sandbox: Sandbox) -> SandboxRestApiSession:
    """Yield CS REST API object."""
    return SandboxRestApiSession(
        REST_SERVER, username=sandbox.automation_api.username, password=sandbox.automation_api.password, domain="Global"
    )


def test_log_to_reservation_output(sandbox: Sandbox, rest_api: SandboxRestApiSession) -> None:
    """Test log to output.

    :todo: Assert on sandbox reservation.
    """
    logger.addHandler(ReservationOutputHandler(sandbox))
    logger.info("Hello World")
    output = rest_api.get_sandbox_output(get_reservation_id(sandbox))
    assert output["entries"][0]["text"] == "Hello World"
