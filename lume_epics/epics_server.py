import time
import logging
import multiprocessing
import os
from typing import Dict, Mapping, Union, List
from threading import Thread
from queue import Full, Empty

from lume_model.variables import Variable, InputVariable, OutputVariable
from lume_model.models import SurrogateModel

from epics import caget
import epics

from p4p.client.thread import Context

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
        prefix: str,
        protocols: List[str] = ["pva", "ca"],
        model_kwargs: dict = {},
        epics_config: dict = {},
        read_only: bool = False,
    ) -> None:
        """Create OnlineSurrogateModel instance in the main thread and
        initialize output variables by running with the input process variable
        state, input/output variable tracking, start the server, create the
        process variables, and start the driver.

        Args:
            model_class (SurrogateModel): Surrogate model class to be
            instantiated.

            prefix (str): Prefix used to format process variables.

            protocols (List[str]): List of protocols used to instantiate server.

            model_kwargs (dict): Kwargs to instantiate model.

            read_only (bool): Indication whether this will be a read-only server

        """
        # check protocol conditions
        if not protocols:
            raise ValueError("Protocol must be provided to start server.")

        if any([protocol not in ["ca", "pva"] for protocol in protocols]):
            raise ValueError(
                'Invalid protocol provided. Protocol options are "pva" '
                '(pvAccess) and "ca" (Channel Access).'
            )

        # Update epics configuration
        for var in EPICS_ENV_VARS:
            if epics_config.get(var):
                os.environ[var] = epics_config[var]

        self.prefix = prefix
        self.protocols = protocols

        self.model = model_class(**model_kwargs)
        self.input_variables = self.model.input_variables

        # track pv monitors
        self._ca_monitors = {}

        # NEED TO CHECK READ ONLY
        if not read_only:
            for variable in self.input_variables.values():
                if variable.value is None:
                    variable.value = variable.default

        # if read_only, get initial values
        elif "ca" in protocols and read_only:

            for variable in self.input_variables.values():
                logger.info("Getting value for %s via caget", variable.name)
                variable.value = caget(f"{prefix}:{variable.name}")
                # monitors must be created at outset as pv caching causes issues with pv callbacks defined in the ca_server
                self._ca_monitors[variable.name] = epics.PV(
                    f"{self.prefix}:{variable.name}", auto_monitor=True
                )

        elif "pva" in protocols and read_only:
            context = Context("pva")
            for variable in self.input_variables.values():
                variable.value = context.get(f"{prefix}:{variable.name}")
                variable.value = 1

            context.close()

        model_input = list(self.input_variables.values())

        self.input_variables = self.model.input_variables
        self.output_variables = self.model.evaluate(model_input)
        self.output_variables = {
            variable.name: variable for variable in self.output_variables
        }

        self.in_queue = multiprocessing.Queue()
        self.out_queues = dict()
        for protocol in protocols:
            self.out_queues[protocol] = multiprocessing.Queue()

        self.exit_event = multiprocessing.Event()

        self._running_indicator = multiprocessing.Value("b", False)
        self._read_only = read_only

        # we use the running marker to make sure pvs + ca don't just keep adding queue elements
        self.comm_thread = Thread(
            target=self.run_comm_thread,
            kwargs={
                "model_kwargs": model_kwargs,
                "in_queue": self.in_queue,
                "out_queues": self.out_queues,
                "running_indicator": self._running_indicator,
            },
        )

        # initialize channel access server
        if "ca" in protocols:
            self.ca_process = CAServer(
                prefix=self.prefix,
                input_variables=self.input_variables,
                output_variables=self.output_variables,
                in_queue=self.in_queue,
                out_queue=self.out_queues["ca"],
                running_indicator=self._running_indicator,
                read_only=self._read_only,
            )

            # add callback to monitors
            for var in self.input_variables:
                self._ca_monitors[var].add_callback(self.ca_process._monitor_callback)

        # initialize pvAccess server
        if "pva" in protocols:

            manager = multiprocessing.Manager()
            self.pva_process = PVAServer(
                prefix=self.prefix,
                input_variables=self.input_variables,
                output_variables=self.output_variables,
                in_queue=self.in_queue,
                out_queue=self.out_queues["pva"],
                running_indicator=self._running_indicator,
                read_only=self._read_only,
            )

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
        model_kwargs={},
        in_queue: multiprocessing.Queue = None,
        out_queues: Dict[str, multiprocessing.Queue] = None,
    ):
        """Handles communications between pvAccess server, Channel Access server, and model.

        Arguments:
            model_class: Model class to be executed.

            model_kwargs (dict): Dictionary of model keyword arguments.

            in_queue (multiprocessing.Queue):

            out_queues (Dict[str: multiprocessing.Queue]): Maps protocol to output assignment queue.

            running_marker (multiprocessing.Value): multiprocessing marker for whether comm thread computing or not

        """
        model = self.model

        while not self.exit_event.is_set():
            try:

                data = in_queue.get(timeout=0.1)

                # mark running
                running_indicator.value = True

                for pv in data["pvs"]:
                    self.input_variables[pv].value = data["pvs"][pv]

                # sync pva/ca
                for protocol, queue in out_queues.items():
                    if protocol == data["protocol"]:
                        continue

                    queue.put(
                        {
                            "input_variables": [
                                self.input_variables[pv] for pv in data["pvs"]
                            ]
                        }
                    )

                # update output variable state
                model_input = list(self.input_variables.values())
                predicted_output = model.evaluate(model_input)
                for protocol, queue in out_queues.items():
                    queue.put({"output_variables": predicted_output}, timeout=0.1)

                running_indicator.value = False

            except Empty:
                continue

            except Full:
                logger.error(f"{protocol} queue is full.")

        logger.info("Stopping comm thread")

    def start(self, monitor: bool = True) -> None:
        """Starts server using set server protocol(s).

        Args:
            monitor (bool): Indicates whether to run the server in the background
                or to continually monitor. If monitor = False, the server must be
                explicitly stopped using server.stop()

        """
        self.comm_thread.start()

        if "ca" in self.protocols:
            self.ca_process.start()

        if "pva" in self.protocols:
            self.pva_process.start()

        if monitor:
            try:
                while True:
                    time.sleep(0.1)

            except KeyboardInterrupt:
                self.stop()

    def stop(self) -> None:
        """Stops the server.

        """
        logger.info("Stopping server.")
        self.exit_event.set()
        self.comm_thread.join()

        if "ca" in self.protocols:
            self.ca_process.shutdown()
            self.ca_process.join()

        if "pva" in self.protocols:
            self.pva_process.shutdown()
            self.pva_process.join()

        logger.info("Server is stopped.")
