"""
Base classes and helpers for traffic generators shells.
"""
import logging
import time
from typing import Optional

from cloudshell.logging.qs_logger import get_qs_logger
from cloudshell.shell.core.context_utils import get_resource_name
from cloudshell.shell.core.driver_context import CancellationContext, InitCommandContext, ResourceCommandContext
from cloudshell.shell.core.resource_driver_interface import ResourceDriverInterface

from .helpers import get_cs_session, get_reservation_id
from .rest_api_helpers import SandboxAttachments

TGN_CHASSIS_FAMILY = "CS_TrafficGeneratorChassis"
TGN_CONTROLLER_FAMILY = "CS_TrafficGeneratorController"
TGN_PORT_FAMILY = "CS_TrafficGeneratorPort"

BREAKINGPOINT_CHASSIS_MODEL = "BreakingPoint Chassis 2G"
BREAKINGPOINT_CONTROLLER_MODEL = "BreakingPoint Controller 2G"
BYTEBLOWER_CHASSIS_MODEL = "ByteBlower Chassis Shell 2G"
BYTEBLOWER_CONTROLLER_MODEL = "ByteBlower Controller Shell 2G"
IXIA_CHASSIS_MODEL = "Ixia Chassis Shell 2G"
IXLOAD_CONTROLLER_MODEL = "IxLoad Controller Shell 2G"
IXNETWORK_CONTROLLER_MODEL = "IxNetwork Controller Shell 2G"
PERFECT_STORM_CHASSIS_MODEL = "PerfectStorm Chassis Shell 2G"
STC_CHASSIS_MODEL = "STC Chassis Shell 2G"
STC_CONTROLLER_MODEL = "STC Controller Shell 2G"
XENA_CHASSIS_MODEL = "Xena Chassis Shell 2G"
XENA_CONTROLLER_MODEL = "Xena Controller Shell 2G"


keep_alive_reservations = []


def is_blocking(blocking: str) -> bool:
    """Return True if the value of `blocking` parameter represents true else returns false.

    :param blocking: Value of `blocking` parameter.
    """
    return blocking.lower() == "true"


def enqueue_keep_alive(context: ResourceCommandContext) -> None:
    """Enqueue TgControllerDriver.keep_alive command to run in the background."""
    if context.reservation.reservation_id in keep_alive_reservations:
        return
    cs_session = get_cs_session(context)
    resource_name = get_resource_name(context=context)
    cs_session.EnqueueCommand(
        reservationId=get_reservation_id(context), targetName=resource_name, targetType="Service", commandName="keep_alive"
    )
    keep_alive_reservations.append(context.reservation.reservation_id)


def attach_stats_csv(
    context: ResourceCommandContext, logger: logging.Logger, view_name: str, output: str, suffix: str = "csv"
) -> str:
    """Attach statistics CSV to reservation."""
    quali_api_helper = SandboxAttachments(context.connectivity.server_address, context.connectivity.admin_auth_token, logger)
    quali_api_helper.login()
    full_file_name = view_name.replace(" ", "_") + "_" + time.ctime().replace(" ", "_") + "." + suffix
    quali_api_helper.attach_new_file(get_reservation_id(context), file_data=output, file_name=full_file_name)
    get_cs_session(context).WriteMessageToReservationOutput(
        get_reservation_id(context), f"Statistics view saved in attached file - {full_file_name}"
    )
    return full_file_name


class TgControllerDriver(ResourceDriverInterface):
    """Base class for all TG controller drivers."""

    def __init__(self) -> None:
        """Initialize object variables, actual initialization is performed in initialize method."""
        self.logger: logging.Logger = None

    def initialize(self, context: InitCommandContext) -> None:
        """Default implementation for abstract method."""
        self.init_loggers(name=context.resource.name)

    def cleanup(self) -> None:
        """Default empty implementation for abstract method."""

    def init_loggers(self, name: str, log_group: str = "traffic_shells", packages_loggers: Optional[list] = None) -> None:
        """Initialize TG loggers."""
        self.logger = get_qs_logger(log_group=log_group, log_file_prefix=name)
        self.logger.setLevel(logging.DEBUG)

        for package_logger_name in packages_loggers or []:
            package_logger = logging.getLogger(package_logger_name)
            package_logger.setLevel(self.logger.level)
            for handler in self.logger.handlers:
                if handler not in package_logger.handlers:
                    package_logger.addHandler(handler)

    def keep_alive(self, context: ResourceCommandContext, cancellation_context: CancellationContext) -> None:
        """A bg command that runs forever to keep the shell, thus the session to the TG, up and running between commands.

        It is the shell driver responsibility to call enqueue_keep_alive during before it creates the session to the TG,
        usually in load_config command.
        """
        while not cancellation_context.is_cancelled:
            time.sleep(2)
        if cancellation_context.is_cancelled:
            self.cleanup()
