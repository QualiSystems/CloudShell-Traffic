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
from cloudshell.traffic.helpers import ReservationOutputHandler
from cloudshell.workflow.orchestration.sandbox import Sandbox

logger = get_qs_logger()
logger.setLevel(logging.DEBUG)


@pytest.fixture()
def session() -> CloudShellAPISession:
    """Yield CloudShell session."""
    return create_session_from_config()


@pytest.fixture()
def test_helpers(session: CloudShellAPISession) -> Iterable[TestHelpers]:
    """Yield configured TestHelpers object with reservation."""
    test_helpers = TestHelpers(session)
    test_helpers.create_reservation()
    yield test_helpers
    test_helpers.end_reservation()


@pytest.fixture()
def sandbox(test_helpers: TestHelpers) -> Sandbox:
    """Yield Sandbox."""
    test_helpers.attach_to_cloudshell_as()
    return Sandbox()


def test_log_to_reservation_output(sandbox: Sandbox) -> None:
    """Test log to output.

    :todo: Assert on sandbox reservation.
    """
    logger.addHandler(ReservationOutputHandler(sandbox))
    logger.info("Hello World")
