import time
import logging
import multiprocessing

try:
    multiprocessing.set_start_method("spawn")
except:
    pass

import os
from typing import Dict, Mapping, Union, List
from threading import Thread, Event
from queue import Full, Empty

import pcaspy

# use correct libca
os.environ["PYEPICS_LIBCA"] = os.path.dirname(pcaspy.__file__)


from lume_model.variables import Variable, InputVariable, OutputVariable
from lume_model.models import SurrogateModel

from lume_epics import EPICS_ENV_VARS
from .epics_pva_server import PVAServer
from .epics_ca_server import CAServer

logger = logging.getLogger(__name__)
logger.setLevel(logging.DEBUG)


class Server:
    """
    Server for EPICS process variables. Can be optionally initialized with only
    pvAccess or Channel Access protocols; but, defaults to serving over both.

    Attributes:
        model (SurrogateModel): SurrogateModel class to be served

        input_variables (List[Variable]): List of lume-model variables passed to model.

        ouput_variables (List[Variable]): List of lume-model variables to use as
            outputs.

        ca_server (SimpleServer): Server class that interfaces between the Channel
            Access client and the driver.

        ca_driver (CADriver): Class used by server to handle to process variable
            read/write requests.

        pva_server (P4PServer): Threaded p4p server used for serving pvAccess
            variables.

        exit_event (Event): Threading exit event marking server shutdown.

    """

    def __init__(
        self,
        model_class: SurrogateModel,
        epics_config: dict,
        model_kwargs: dict = {},
        epics_env: dict = {},
    ) -> None:
        """Create OnlineSurrogateModel instance in the main thread and
        initialize output variables by running with the input process variable
        state, input/output variable tracking, start the server, create the
        process variables, and start the driver.

        Args:
            model_class (SurrogateModel): Surrogate model class to be
            instantiated.

            epics_config (dict): Dictionary describing EPICS configuration for model variables

            model_kwargs (dict): Kwargs to instantiate model.

            epics_env (dict): Environment variables for EPICS configuration

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
                for var_name, var in self.input_variables.items()
                if var_name in ca_config
            }
            ca_output_vars = {
                var_name: var
                for var_name, var in self.output_variables.items()
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
        """Handle server startup
        """
        self.start(monitor=False)
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        """Handle server shutdown
        """
        self.stop()

    def run_comm_thread(
        self,
        *,
        running_indicator: multiprocessing.Value,
        in_queue: multiprocessing.Queue = None,
        out_queues: Dict[str, multiprocessing.Queue] = None,
    ):
        """Handles communications between pvAccess server, Channel Access server, and model.

        Arguments:
            model_class: Model class to be executed.

            in_queue (multiprocessing.Queue):

            out_queues (Dict[str: multiprocessing.Queue]): Maps protocol to output assignment queue.

            running_marker (multiprocessing.Value): multiprocessing marker for whether comm thread computing or not

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
                            inputs = [
                                self.input_variables[var]
                                for var in data["vars"]
                                if self._epics_config[var]["protocol"]
                                in [protocol, "both"]
                            ]

                            if len(inputs):
                                queue.put({"input_variables": inputs})

                    model_input = list(self.input_variables.values())

                    try:
                        predicted_output = model.evaluate(model_input)

                        for protocol, queue in out_queues.items():
                            outputs = [
                                var
                                for var in predicted_output
                                if var.name in self._pva_fields
                                or self._epics_config[var.name]["protocol"]
                                in [protocol, "both"]
                            ]
                            queue.put({"output_variables": outputs}, timeout=0.1)
                    except Exception as e:
                        print(e)
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
            monitor (bool): Indicates whether to run the server in the background
                or to continually monitor. If monitor = False, the server must be
                explicitly stopped using server.stop()

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
        """Stops the server.

        """
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
