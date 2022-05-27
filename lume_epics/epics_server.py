import time
import logging
import multiprocessing
import traceback

try:
    multiprocessing.set_start_method("spawn")
except:
    pass

import os
from typing import Dict, List, Type, Optional
from threading import Thread, Event
from queue import Full, Empty

# require import for libca config
import pcaspy

# use correct libca
os.environ["PYEPICS_LIBCA"] = os.path.dirname(pcaspy.__file__)


from lume_model.variables import Variable, InputVariable, OutputVariable
from lume_model.models import BaseModel

from lume_epics import EPICS_ENV_VARS
from .epics_pva_server import PVAServer
from .epics_ca_server import CAServer

logger = logging.getLogger(__name__)
logger.setLevel(logging.DEBUG)


class Server:
    """
    Server for EPICS process variables. Can be optionally initialized with only
    pvAccess or Channel Access protocols.

    Attributes:
        model (BaseModel): Instantiated model

        input_variables (Dict[str: InputVariable]): Model input variables

        output_variables (Dict[str: OutputVariable]): Model output variables

        epics_config (Optional[Dict]): ...

        _pva_fields (List[str]): List of variables pointing to pvAccess fields

        _protocols (List[str]): List of protocols in use

        in_queue (multiprocessing.Queue):

        out_queues (Dict[str, multiprocessing.Queue]): Queue updates to output
            variables to protocol servers.

        exit_event (multiprocessing.Event): Event triggering shutdown

        _running_indicator (multiprocessing.Value): Value indicating whether server is running

        _process_exit_events (List[multiprocessing.Event]): Exit events for each process

        _model_exec_exit_event (Event): Thread event for model execution exceptions

        comm_thread (Thread): Thread for model execution

        ca_process (multiprocessing.Process): Channel access server process

        pva_process (multiprocessing.Process): pvAccess server process

    """

    def __init__(
        self,
        model_class: Type[BaseModel],
        epics_config: dict,
        model_kwargs: dict = {},  # TODO DROP and use instantiated mode
        epics_env: dict = {},  # TODO drop hashable default. Should be Optional[dict]
    ) -> None:
        """Create model_class instance and configure both Channel Access and pvAccess
        servers for execution.

        Args:
            model_class (Type[BaseModel]): Model class to be instantiated

            epics_config (dict): Dictionary describing EPICS configuration for model
                variables.

            model_kwargs (dict): Kwargs to instantiate model.

            epics_env (dict): Environment variables for EPICS configuration.

        """

        # Update epics environment if programatically set
        for var in EPICS_ENV_VARS:
            if epics_env.get(var):
                os.environ[var] = epics_env[var]

        self.model = model_class(**model_kwargs)
        self.input_variables = self.model.input_variables
        self.output_variables = self.model.output_variables

        self._epics_config = epics_config

        # define programatic access to model summary
        self._pvname = None
        self._owner = None
        self._date_published = None
        self._description = None
        self._id = None

        # If configured, set up summary pv
        if "summary" in self._epics_config:
            self._pvname = self._epics_config["summary"].get("pvname")
            self._owner = self._epics_config["summary"].get("owner", "")
            self._date_published = self._epics_config["summary"].get(
                "date_published", ""
            )
            self._description = self._epics_config["summary"].get("description", "")
            self._id = self._epics_config["summary"].get("id", "")

        self._protocols = []

        ca_config = {
            var: self._epics_config[var]
            for var in self._epics_config
            if self._epics_config[var].get("protocol") in ["ca", "both"]
        }
        pva_config = {
            var: self._epics_config[var]
            for var in self._epics_config
            if self._epics_config[var].get("protocol") in ["pva", "both"]
            or var == "summary"
        }

        # track nested fields
        self._pva_fields = []
        for var, config in self._epics_config.items():
            if config.get("fields"):
                self._pva_fields += config["fields"]

        if len(ca_config) > 0:
            self._protocols.append("ca")

        if len(pva_config) > 0:
            self._protocols.append("pva")

        # set up protocol based queues
        self.in_queue = multiprocessing.Queue()
        self.out_queues = dict()
        for protocol in self._protocols:
            self.out_queues[protocol] = multiprocessing.Queue()

        # exit event for triggering shutdown
        self.exit_event = multiprocessing.Event()
        self._running_indicator = multiprocessing.Value("b", False)
        self._process_exit_events = []

        # event for shutdown on model execution exceptions
        self._model_exec_exit_event = Event()

        # we use the running marker to make sure pvs + ca don't just keep adding queue elements
        self.comm_thread = Thread(
            target=self.run_comm_thread,
            kwargs={
                "in_queue": self.in_queue,
                "out_queues": self.out_queues,
                "running_indicator": self._running_indicator,
            },
        )

        # initialize channel access server
        if "ca" in self._protocols:
            ca_input_vars = {
                var_name: var
                for var_name, var in self.model.input_variables.items()
                if var_name in ca_config
            }
            ca_output_vars = {
                var_name: var
                for var_name, var in self.model.output_variables.items()
                if var_name in ca_config
            }

            self.ca_process = CAServer(
                input_variables=ca_input_vars,
                output_variables=ca_output_vars,
                epics_config=ca_config,
                in_queue=self.in_queue,
                out_queue=self.out_queues["ca"],
                running_indicator=self._running_indicator,
            )

            self._process_exit_events.append(self.ca_process.exit_event)

        # initialize pvAccess server
        if "pva" in self._protocols:
            pva_input_vars = {
                var_name: var
                for var_name, var in self.input_variables.items()
                if var_name in pva_config
            }
            pva_output_vars = {
                var_name: var
                for var_name, var in self.output_variables.items()
                if var_name in pva_config
            }

            self.pva_process = PVAServer(
                input_variables=pva_input_vars,
                output_variables=pva_output_vars,
                epics_config=pva_config,
                in_queue=self.in_queue,
                out_queue=self.out_queues["pva"],
                running_indicator=self._running_indicator,
            )

            self._process_exit_events.append(self.pva_process.exit_event)

    def __enter__(self):
        """Handle server startup"""
        self.start(monitor=False)
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        """Handle server shutdown"""
        self.stop()

    def run_comm_thread(
        self,
        *,
        running_indicator: multiprocessing.Value,
        in_queue: Optional[multiprocessing.Queue],
        out_queues: Optional[Dict[str, multiprocessing.Queue]],
    ):
        """Handles communications between pvAccess server, Channel Access server, and
             dmodel.

        Arguments:
            running_indicator (multiprocessing.Value): Indicates whether main server
                process active.

            in_queue (Optional[multiprocessing.Queue]): Queue receiving input variable
                inputs.

            out_queues (Optional[Dict[str, multiprocessing.Queue]]): Queue for communicating
                output vars with servers.

        """
        model = self.model
        inputs_initialized = 0

        while not self.exit_event.is_set():
            try:
                data = in_queue.get(timeout=0.1)

                # mark running
                running_indicator.value = True

                for var in data["vars"]:
                    self.input_variables[var] = data["vars"][var]

                # check no input values are None
                if not any(
                    [var.value is None for var in self.input_variables.values()]
                ):
                    inputs_initialized = 1

                # update output variable state
                if inputs_initialized:

                    # sync pva/ca if duplicated
                    for protocol, queue in out_queues.items():
                        if protocol != data["protocol"]:
                            inputs = {
                                var: self.input_variables[var]
                                for var in data["vars"]
                                if self._epics_config[var]["protocol"]
                                in [protocol, "both"]
                            }

                            if len(inputs):
                                queue.put({"input_variables": inputs})

                    model_input = self.input_variables

                    try:
                        predicted_output = model.evaluate(model_input)

                        for protocol, queue in out_queues.items():
                            outputs = {
                                var.name: var
                                for var in predicted_output.values()
                                if var.name in self._pva_fields
                                or self._epics_config[var.name]["protocol"]
                                in [protocol, "both"]
                            }
                            queue.put({"output_variables": outputs}, timeout=0.1)

                    except Exception as e:
                        traceback.print_exc()
                        self._model_exec_exit_event.set()

                running_indicator.value = False

            except Empty:
                continue

            except Full:
                logger.error(f"{protocol} queue is full.")

        logger.info("Stopping execution thread")

    def start(self, monitor: bool = True) -> None:
        """Starts server using set server protocol(s).

        Args:
            monitor (bool): Indicates whether to run the server in the background or to
                continually monitor. If monitor = False, the server must be explicitly
                stopped using server.stop()

        """
        self.comm_thread.start()

        if "ca" in self._protocols:
            self.ca_process.start()

        if "pva" in self._protocols:
            self.pva_process.start()

        if monitor:
            try:
                while not any(
                    [
                        exit_event.is_set()
                        for exit_event in self._process_exit_events
                        + [self._model_exec_exit_event]
                    ]
                ):
                    time.sleep(0.1)

                # shut down server if process exited.
                self.stop()

            except KeyboardInterrupt:
                self.stop()

    def stop(self) -> None:
        """Stops the server."""
        logger.info("Stopping server.")
        self.exit_event.set()
        self.comm_thread.join()

        if "ca" in self._protocols:
            self.ca_process.shutdown()

        if "pva" in self._protocols:
            self.pva_process.shutdown()

        logger.info("Server is stopped.")

    @property
    def summary(self):
        return {
            "pvname": self._pvname,
            "owner": self._owner,
            "date published": self._date_published,
            "description": self._description,
            "id": self._id,
        }

    @property
    def owner(self):
        return self._owner

    @property
    def summary_pvname(self):
        return self._pvname

    @property
    def date_published(self):
        return self._date_published

    @property
    def description(self):
        return self._description

    @property
    def id(self):
        return self._id
