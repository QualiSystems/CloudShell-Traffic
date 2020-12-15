import json
import logging
from collections import OrderedDict
from ipaddress import ip_address, AddressValueError
from io import StringIO
from multiprocessing.dummy import Pool as ThreadPool
from typing import Optional, Union, List, Dict

from netaddr.eui import EUI
from netaddr.core import AddrFormatError
from netaddr.strategy.eui48 import mac_cisco

from cloudshell.api.cloudshell_api import (CloudShellAPISession, InputNameValue, ServiceInstance, FindResourceInfo,
                                           AttributeNameValue)
from cloudshell.logging.qs_logger import get_qs_logger
from cloudshell.shell.core.driver_context import ResourceCommandContext
from cloudshell.shell.core.resource_driver_interface import ResourceDriverInterface
from cloudshell.shell.core.session.cloudshell_session import CloudShellSessionContext
from cloudshell.workflow.orchestration.sandbox import Sandbox

from cloudshell.traffic.helpers import (get_reservation_id, get_reservation_description, get_services_from_reservation,
                                        WriteMessageToReservationOutputHandler)
from cloudshell.traffic.health_check_reports import create_html
from cloudshell.traffic.quali_rest_api_helper import QualiAPIHelper

ACS_MODEL = 'Acs'
CABLE_MODEM_FAMILY = 'CS_CableModem'
CABLE_MODEM_MODEL = 'Cable_Modem'
CPE_MODEL = 'Cpe'
CNR_MODEL = 'Cnr'
HEALTH_CHECK_STATUS_MODEL = 'Healthcheck_Status'
JIRA_MODEL = 'Jira'
L1_SPLITTER_MODEL = 'L1 Splitter 2 Chassis'
REDIRECT_DB_MODEL = 'Redirect_DB'
RESOURCE_PROVIDER_MODEL = 'Resource_Provider'


def get_health_check_service(context: Union[ResourceCommandContext, Sandbox], object_name: str,
                             status_selector: Optional[str] = 'none') -> ServiceInstance:
    """ Set the live status attribute for a health check status service connected to an object (resource of service).

    :param context: Resource command context.
    :param object_name: The object that the health check service is connected to.
    :param status_selector: Selects the requested health check status service in case multiple services are connected
        to the resource.
    """
    description = get_reservation_description(context)
    resource_connectors = [c for c in description.Connectors if object_name in [c.Source, c.Target]]
    for connector in resource_connectors:
        other_end_name = connector.Target if connector.Source == object_name else connector.Source
        other_end_services = [s for s in description.Services if s.Alias == other_end_name]
        if other_end_services:
            other_end_service = other_end_services[0]
            if other_end_service.ServiceName == HEALTH_CHECK_STATUS_MODEL:
                a_name = f'{HEALTH_CHECK_STATUS_MODEL}.status_selector'
                hc_service_selector = [a for a in other_end_service.Attributes if a.Name == a_name][0].Value
                if hc_service_selector == status_selector:
                    return other_end_service


def set_health_check_live_status(context: ResourceCommandContext, object_name: str, status: bool,
                                 status_selector: Optional[str] = 'none') -> ServiceInstance:
    """ Set the live status attribute for a health check status service connected to an object (resource of service).

    :param context: Resource command context.
    :param object_name: The object that the health check service is connected to.
    :param status: True will set the live status to Online, False will set the live status to Error.
    :param status_selector: Selects the requested health check status service in case multiple services are connected
        to the resource.
    """
    hc_service = get_health_check_service(context, object_name, status_selector)
    if hc_service:
        cs_session = CloudShellAPISession(host=context.connectivity.server_address,
                                          token_id=context.connectivity.admin_auth_token,
                                          domain=context.reservation.domain)
        cs_session.ExecuteCommand(get_reservation_id(context), hc_service.Alias, 'Service',
                                  'set_live_status',
                                  [InputNameValue('status', 'Online' if status else 'Error')])
    return hc_service


class HealthCheckDriver(ResourceDriverInterface):
    """ Base class for all Health Check resource drivers. """

    def initialize(self, context, resource, log_group='health_check_shells', packages_loggers=None):

        super().initialize(context)

        self.resource = resource
        self.service = resource

        self.logger = get_qs_logger(log_group=log_group, log_file_prefix=context.resource.name)
        self.logger.setLevel(logging.DEBUG)

        for package_logger in packages_loggers or ['pycmts', 'pycnr', 'pylgi']:
            package_logger = logging.getLogger(package_logger)
            package_logger.setLevel(self.logger.level)
            for handler in self.logger.handlers:
                if handler not in package_logger.handlers:
                    package_logger.addHandler(handler)

        self.get_connection_details(context)

    def cleanup(self):
        pass

    def get_connection_details(self, context):
        self.address = context.resource.address
        self.logger.debug(f'Address - {self.address}')
        self.user = self.resource.user
        self.logger.debug(f'User - {self.user}')
        self.logger.debug(f'Encrypted password - {self.resource.password}')
        try:
            self.password = CloudShellSessionContext(context).get_api().DecryptPassword(self.resource.password).Value
        except Exception as _:
            # Some models use clear text passwords or ignore the password altogether.
            self.password = self.resource.password
        self.logger.debug(f'Password - {self.password}')

    @property
    def clean_report(self) -> OrderedDict:
        """ Creates a clean report dict. """
        return OrderedDict({'name': '', 'result': False, 'status': '', 'summary': {}, 'log': {}})


EMPTY_ADDRESS_ERROR_MESSAGE = ('\nINPUT ERROR: Address cannot be empty\n'
                               'Go to SANDBOX -> Properties -> Parameters and set MAC/IP Address\n'
                               'Then run COMMANDS -> Setup again\n\n')
INVALID_ADDRESS_ERROR_MESSAGE = ('\nINPUT ERROR: Invalid Address {}\n'
                                 'Go to SANDBOX -> Properties -> Parameters and reset MAC/IP Address\n'
                                 'Then run COMMANDS -> Setup again\n\n')


class HealthCheckOrchestration:
    """ Base orchestration script for health check blueprints. """

    def __init__(self, sandbox: Sandbox, debug: Optional[bool] = False) -> None:
        """ Init sandbox APIs and loggers.

        :param sandbox: current sandbox object.
        :param debug: True - run in debug mode and send logs to the reservation console, False - non debug mode.
        """
        self.sandbox: Sandbox = sandbox
        self.api: CloudShellAPISession = self.sandbox.automation_api
        self.debug = debug
        if self.debug:
            self.sandbox.logger.setLevel(logging.DEBUG)
        sandbox.logger.addHandler(WriteMessageToReservationOutputHandler(self.sandbox))

        self.health_checks = OrderedDict()

    def _validate_mac_address(self, address) -> Optional[str]:
        """ Validate that input MAC address is valid - raise error if not.

        :param address: MAC address to validate, supports all MacUtils formats.
        """
        if address:
            try:
                mac = EUI(address)
                mac.dialect = mac_cisco
                return str(mac)
            except AddrFormatError as e:
                self.api.WriteMessageToReservationOutput(reservationId=self.sandbox.id,
                                                         message=INVALID_ADDRESS_ERROR_MESSAGE.format(address))
                raise ValueError(f'Invalid MAC address - {address}') from e
        else:
            self.api.WriteMessageToReservationOutput(reservationId=self.sandbox.id, message=EMPTY_ADDRESS_ERROR_MESSAGE)
            raise ValueError('MAC address cannot be empty')

    def _validate_ip_address(self, address) -> Optional[str]:
        """ Validate that input IP address is valid - raise error if not.

        :param address: IP address to validate, supports all MacUtils formats.
        """
        if address:
            try:
                return str(ip_address(address))
            except AddressValueError as e:
                self.api.WriteMessageToReservationOutput(reservationId=self.sandbox.id,
                                                         message=INVALID_ADDRESS_ERROR_MESSAGE.format(address))
                raise ValueError(f'Invalid IP address - {address}') from e
        else:
            self.api.WriteMessageToReservationOutput(reservationId=self.sandbox.id, message=EMPTY_ADDRESS_ERROR_MESSAGE)
            raise ValueError('IP address cannot be empty')

    def _get_provider_for_model(self, model: str) -> ServiceInstance:
        """ Returns the provider service for the requested model.

        :param model: Requested model.
        """
        providers = get_services_from_reservation(self.sandbox, RESOURCE_PROVIDER_MODEL)
        for provider in providers:
            provider_model = [a.Value for a in provider.Attributes
                              if a.Name == f'{provider.ServiceName}.resource_model'][0]
            if provider_model.lower() in model.lower():
                return provider
        raise ValueError(f'Provider service for {model} resource not found in reservation')

    def _set_provider_attrs(self, resource: FindResourceInfo) -> None:
        """ Set provider service attributes with requested resource values.

        :param resource: Resource to provide.
        """
        if resource:
            provider = self._get_provider_for_model(resource.ResourceModelName)
            attributes = [AttributeNameValue(f'{provider.ServiceName}.resource_model', resource.ResourceModelName),
                          AttributeNameValue(f'{provider.ServiceName}.resource_name', resource.Name)]
            self.api.SetServiceAttributesValues(reservationId=self.sandbox.id, serviceAlias=provider.Alias,
                                                attributeRequests=attributes)

    def _replace_all(self, providers: List[ServiceInstance], parallel: Optional[bool] = True) -> Dict[str, object]:
        """ Replace all services with concrete resources.

        Report error if there is sufficient info to provide. It is the caller responsibility to report missing info.

        :param providers: List of providers to activate.
        :param parallel: If True run replace commands in parallel, else run sequentially.
        """
        outputs = {}
        if parallel:
            pool = ThreadPool(len(providers))
            for provider in providers:
                pool.apply_async(self._execute_target_command, (provider, 'replace_with_concrete', []))
            pool.close()
            pool.join()
        else:
            for provider in providers:
                resource_name_attr_name = f'{provider.ServiceName}.resource_name'
                resource_name = [a.Value for a in provider.Attributes if a.Name == resource_name_attr_name][0]
                if resource_name:
                    outputs[resource_name] = self._execute_target_command(provider, 'replace_with_concrete', [])
                    if isinstance(outputs[resource_name], Exception):
                        self.api.SetServiceLiveStatus(reservationId=self.sandbox.id, serviceAlias=provider.Alias,
                                                      liveStatusName='Error', additionalInfo='tool_tip')
                else:
                    self.api.SetServiceLiveStatus(reservationId=self.sandbox.id, serviceAlias=provider.Alias,
                                                  liveStatusName='Error', additionalInfo='tool_tip')
        return outputs

    def _health_check_group(self, health_checks: List[str], parallel: Optional[bool] = True) -> None:
        """ Run group of health check commands.

        :param health_checks: List of health checks (keys in self.health_checks dict) to run.
        :param parallel: If True run health check commands in parallel, else run sequentially.
        """
        if parallel:
            pool = ThreadPool(len(health_checks))
            async_results = {}
            for health_check in health_checks:
                hc = self.health_checks[health_check]
                async_results[health_check] = pool.apply_async(self._execute_target_command,
                                                               (hc['resource'], hc['command'], hc['inputs']))
            pool.close()
            pool.join()
            for health_check, result in async_results.items():
                # todo: handle isinstance(results, Exception)
                self.health_checks[health_check]['results'] = result.get()
        else:
            for health_check in health_checks:
                hc = self.health_checks[health_check]
                results = self._execute_target_command(hc['resource'], hc['command'], hc['inputs'])
                if isinstance(results, Exception):
                    report = {'name': hc['resource'].Name,
                              'result': False,
                              'status': str(results),
                              'summary': {},
                              'log': {}}
                    results = {'report': report,
                               'log': report['status']}
                hc['results'] = results

    def _execute_target_command(self, target: Union[FindResourceInfo, ServiceInstance], command_name: str,
                                command_inputs: List[InputNameValue]) -> Union[dict, Exception]:
        """ Execute command on target resource or service.

        :param target: Target resource or service in reservation.
        :param command_name: Command name.
        :param command_inputs: List of command inputs.
        """
        if type(target) is ServiceInstance:
            target_name = target.Alias
            target_type = 'Service'
        else:
            target_name = target.Name
            target_type = 'Resource'
        try:
            self.sandbox.logger.debug(f'Running command {command_name} on {target_name}')
            command_inputs_msg = ' '.join([f'{ci.Name}={ci.Value}' for ci in command_inputs])
            self.sandbox.logger.debug(f'\tInputs: {command_inputs_msg}')
            result = self.api.ExecuteCommand(reservationId=self.sandbox.id, targetName=target_name,
                                             commandName=command_name, commandInputs=command_inputs,
                                             targetType=target_type)
            output = json.loads(result.Output) if result.Output else None
        except Exception as e:
            self.sandbox.logger.warning(f'Failed to run command {command_name} on {target_name} - {e}')
            output = e
        return output

    def _create_report(self, reports: Dict[str, dict]) -> None:
        """ Create HTML and log reports and attach them to reservation.

        :param reports: reservation reports.
        """
        api_helper = QualiAPIHelper(self.api.host, self.sandbox.logger, self.api.username, self.api.password)
        api_helper.login()
        html_data = create_html(reports)
        file_stream = StringIO()
        file_stream.write(html_data)
        file_stream.seek(0)
        api_helper.attach_new_file(self.sandbox.id, file_stream, 'health_check_report.html')
        file_stream = StringIO()
        for name, report in reports.items():
            file_stream.write(name)
            file_stream.write('\n')
            file_stream.write(report['log'])
        file_stream.seek(0)
        api_helper.attach_new_file(self.sandbox.id, file_stream, 'health_check_log.txt')

    def _set_status(self, reports: dict) -> bool:
        """ Calculate and set sandbox status.

        :param reports: Reports that the status decision will use to calculate the decision.
        """
        failures = [r for r in reports.values() if not r['report']['result']]
        if not failures:
            self.api.SetReservationLiveStatus(reservationId=self.sandbox.id, liveStatusName='Completed successfully',
                                              additionalInfo='Health check passed, environment ready')
        else:
            self.api.SetReservationLiveStatus(reservationId=self.sandbox.id, liveStatusName='Error',
                                              additionalInfo='Health check failed, please check the attached report')
        return failures == []
