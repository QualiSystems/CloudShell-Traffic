"""
Helpers for cloudshell traffic shells and scripts.
"""
import logging
import re
import time
from typing import List, Union

from cloudshell.api.cloudshell_api import (
    CloudShellAPISession,
    CreateReservationResponseInfo,
    ReservationDescriptionInfo,
    ReservedResourceInfo,
    ServiceInstance,
)
from cloudshell.shell.core.driver_context import ResourceCommandContext
from cloudshell.shell.core.session.cloudshell_session import CloudShellSessionContext
from cloudshell.workflow.orchestration.sandbox import Sandbox


class ReservationOutputHandler(logging.Handler):
    """Logger handler to write log messages to reservation output."""

    def __init__(self, context_or_sandbox: Union[ResourceCommandContext, Sandbox]) -> None:
        """Initialize session and sandbox ID."""
        self.session = get_cs_session(context_or_sandbox)
        self.sandbox_id = get_reservation_id(context_or_sandbox)
        super().__init__()

    def emit(self, record: logging.LogRecord) -> None:
        """Log the specified logging record to reservation output."""
        log_entry = self.format(record)
        self.session.WriteMessageToReservationOutput(self.sandbox_id, log_entry)


def get_cs_session(cs_object: Union[ResourceCommandContext, Sandbox, CreateReservationResponseInfo]) -> CloudShellAPISession:
    """Get CS session from context."""
    try:
        return cs_object.automation_api
    except AttributeError:
        pass
    try:
        return CloudShellSessionContext(cs_object).get_api()
    except Exception:  # pylint: disable=broad-except
        pass
    return CloudShellAPISession(
        cs_object.connectivity.server_address,
        token_id=cs_object.connectivity.admin_auth_token,
        domain=cs_object.reservation.domain,
    )


def get_reservation_id(cs_object: Union[CreateReservationResponseInfo, Sandbox, ResourceCommandContext]) -> str:
    """Return reservation ID from context, sandbox, or reservation.

    Do not add type hinting as there are way too many around cloudshell API.
    """
    try:
        return cs_object.id
    except AttributeError:
        pass
    try:
        return cs_object.reservation.reservation_id  # type: ignore[attr-defined]
    except AttributeError:
        pass
    try:
        return cs_object.reservation.id  # type: ignore[attr-defined]
    except AttributeError:
        pass
    try:
        return cs_object.Reservation.Id
    except AttributeError:
        pass
    raise AttributeError(f"Could not get reservation ID from {cs_object}")


def get_reservation_description(context_or_sandbox: Union[ResourceCommandContext, Sandbox]) -> ReservationDescriptionInfo:
    """Get reservation description."""
    reservation_id = get_reservation_id(context_or_sandbox)
    cs_session = get_cs_session(context_or_sandbox)
    return cs_session.GetReservationDetails(reservation_id, disableCache=True).ReservationDescription


def get_family_attribute(
    context_or_sandbox: Union[ResourceCommandContext, Sandbox], resource_name: str, attribute: str
) -> str:
    """Get value of resource attribute.

    Supports 2nd gen shell namespace by pre-fixing family/model namespace.
    """
    cs_session = get_cs_session(context_or_sandbox)
    res_details = cs_session.GetResourceDetails(resource_name)
    res_model = res_details.ResourceModelName
    res_family = res_details.ResourceFamilyName

    # check against all 3 possibilities
    model_attribute = f"{res_model}.{attribute}"
    family_attribute = f"{res_family}.{attribute}"
    attribute_names = [attribute, model_attribute, family_attribute]
    return [attr for attr in res_details.ResourceAttributes if attr.Name in attribute_names][0].Value


def set_family_attribute(
    context_or_sandbox: Union[ResourceCommandContext, Sandbox], resource_name: str, attribute: str, value: str
) -> None:
    """Set value of resource attribute.

    Supports 2nd gen shell namespace by pre-fixing family/model namespace.
    """
    cs_session = get_cs_session(context_or_sandbox)
    res_details = cs_session.GetResourceDetails(resource_name)
    res_model = res_details.ResourceModelName
    res_family = res_details.ResourceFamilyName

    model_attribute = f"{res_model}.{attribute}"
    family_attribute = f"{res_family}.{attribute}"
    attribute_names = [attribute, model_attribute, family_attribute]
    actual_attribute = [attr for attr in res_details.ResourceAttributes if attr.Name in attribute_names][0].Name
    cs_session.SetAttributeValue(resource_name, actual_attribute, value)


def add_resource_to_db(
    context: ResourceCommandContext,
    resource_model: str,
    resource_full_name: str,
    resource_address: str = "na",
    **attributes: str,
) -> None:
    """Add resource to cloudshell DB if not already exist."""
    cs_session = get_cs_session(context)
    resources_w_requested_name = cs_session.FindResources(resourceFullName=resource_full_name).Resources
    if len(resources_w_requested_name) > 0:
        return
    cs_session.CreateResource(resourceModel=resource_model, resourceName=resource_full_name, resourceAddress=resource_address)
    if context.reservation.domain != "Global":
        cs_session.AddResourcesToDomain(domainName=context.reservation.domain, resourcesNames=[resource_full_name])
    for attribute, value in attributes.items():
        set_family_attribute(context, resource_full_name, attribute, value)


def wait_for_resources(
    cs_session: CloudShellAPISession, reservation_id: str, resources_names: Union[list, str], timeout: int = 4
) -> None:
    """Wait until all resources show in reservation details."""
    if isinstance(resources_names, str):
        resources_names = [resources_names]
    for _ in range(timeout + 1):
        all_resources = cs_session.GetReservationDetails(reservation_id).ReservationDescription.Resources
        new_resources = [r for r in all_resources if r.Name in resources_names]
        if len(new_resources) == len(resources_names):
            return
        time.sleep(1)
    raise TimeoutError(f"Resources {resources_names} not in reservation after {timeout} seconds")


def wait_for_services(
    cs_session: CloudShellAPISession, reservation_id: str, aliases: Union[list, str], timeout: int = 4
) -> None:
    """Wait until all services show in reservation details."""
    if isinstance(aliases, str):
        aliases = [aliases]
    for _ in range(timeout + 1):
        all_services = cs_session.GetReservationDetails(reservation_id).ReservationDescription.Services
        new_services = [s for s in all_services if s.Alias in aliases]
        if len(new_services) == len(aliases):
            return
        time.sleep(1)
    raise TimeoutError(f"Services {aliases} not in reservation after {timeout} seconds")


def wait_for_connectors(
    cs_session: CloudShellAPISession, reservation_id: str, aliases: Union[list, str], timeout: int = 4
) -> None:
    """Wait until all connectors show in reservation details."""
    if isinstance(aliases, str):
        aliases = [aliases]
    for _ in range(timeout + 1):
        all_connectors = cs_session.GetReservationDetails(reservation_id).ReservationDescription.Connectors
        new_connectors = [c for c in all_connectors if c.Alias in aliases]
        if len(new_connectors) == len(aliases):
            return
        time.sleep(1)
    raise TimeoutError(f"Connectors {aliases} not in reservation after {timeout} seconds")


# pylint: disable=too-many-arguments
def wait_for_attribute(
    cs_session: CloudShellAPISession,
    reservation_id: str,
    alias: str,
    attribute_name: str,
    attribute_value: str,
    timeout: int = 4,
) -> None:
    """Wait until an attribute that was set is updated on the sandbox."""
    for _ in range(timeout + 1):
        all_services = cs_session.GetReservationDetails(reservation_id).ReservationDescription.Services
        service = [s for s in all_services if s.Alias == alias][0]
        current_attribute_value = [a.Value for a in service.Attributes if a.Name == attribute_name][0]
        if current_attribute_value == attribute_value:
            return
        time.sleep(1)


def get_resources_from_reservation(
    context_or_sandbox: Union[ResourceCommandContext, Sandbox], *resource_models: str
) -> List[ReservedResourceInfo]:
    """Get all resources with the requested resource model names."""
    resources = get_reservation_description(context_or_sandbox).Resources
    return [r for r in resources if r.ResourceModelName in resource_models]


def get_services_from_reservation(
    context_or_sandbox: Union[ResourceCommandContext, Sandbox], *service_names: str
) -> List[ServiceInstance]:
    """Get all services with the requested service names."""
    services = get_reservation_description(context_or_sandbox).Services
    return [s for s in services if s.ServiceName in service_names]


def get_location(port_resource: ReservedResourceInfo) -> str:
    """Extract port location in format ip/module/port from port full address.

    :param port_resource: Port resource object.
    """
    return re.sub(r"M|PG[0-9]+/|P", "", port_resource.FullAddress)
