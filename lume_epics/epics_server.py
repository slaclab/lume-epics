import time
import logging
import threading
import multiprocessing
from typing import Dict, Mapping, Union, List

from threading import Thread, Event, local
from queue import Full, Empty

from lume_model.variables import Variable, InputVariable, OutputVariable
from lume_model.models import SurrogateModel
from .epics_pva_server import PVAServer
from .epics_ca_server import CAServer

logger = logging.getLogger(__name__)


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
        input_variables: List[InputVariable],
        output_variables: List[OutputVariable],
        prefix: str,
        protocols: List[str] = ["pva", "ca"],
        model_kwargs: dict = {},
    ) -> None:
        """Create OnlineSurrogateModel instance in the main thread and
        initialize output variables by running with the input process variable
        state, input/output variable tracking, start the server, create the
        process variables, and start the driver.

        Args:
            model_class (SurrogateModel): Surrogate model class to be
            instantiated.

            input_variables (List[InputVariable]): Model input variables.
            
            output_variables (Lis[OutputVariable]): Model output variables.

            prefix (str): Prefix used to format process variables.

            protocols (List[str]): List of protocols used to instantiate server.

            model_kwargs (dict): Kwargs to instantiate model.


        """
        # check protocol conditions
        if not protocols:
            raise ValueError("Protocol must be provided to start server.")

        if any([protocol not in ["ca", "pva"] for protocol in protocols]):
            raise ValueError(
                'Invalid protocol provided. Protocol options are "pva" '
                '(pvAccess) and "ca" (Channel Access).'
            )

        # need these to be global to access from threads
        self.prefix = prefix
        self.protocols = protocols

        self.input_variables = input_variables
        self.output_variables = output_variables

        # update inputs for starting value to be the default
        for variable in self.input_variables.values():
            if variable.value is None:
                variable.value = variable.default

        model = model_class(**model_kwargs)
        model_input = list(self.input_variables.values())
        self.output_variables = model.evaluate(model_input)
        self.output_variables = {
            variable.name: variable for variable in self.output_variables
        }

        self.in_queue = multiprocessing.Queue()
        self.out_queues = dict()
        for protocol in protocols:
            self.out_queues[protocol] = multiprocessing.Queue()

        self.exit_event = Event()

        self.comm_thread = threading.Thread(
            target=self.run_comm_thread,
            args=(model_class,),
            kwargs={
                "model_kwargs": model_kwargs,
                "in_queue": self.in_queue,
                "out_queues": self.out_queues
            }
        )

        self.ca_process = CAServer(
            prefix=self.prefix,
            input_variables=self.input_variables,
            output_variables=self.output_variables,
            in_queue=self.in_queue,
            out_queue=self.out_queues["ca"]
        )
        self.pva_process = PVAServer(
            prefix=self.prefix,
            input_variables=self.input_variables,
            output_variables=self.output_variables,
            in_queue=self.in_queue,
            out_queue=self.out_queues["pva"]
        )

    def run_comm_thread(self, model_class, model_kwargs={}, in_queue: multiprocessing.Queue=None,
                        out_queues: Dict[str, multiprocessing.Queue]=None):
        """Handles communications between pvAccess server, Channel Access server, and model.
        
        Arguments:
            model_class: Model class to be executed.

            model_kwargs (dict): Dictionary of model keyword arguments.

            in_queue (multiprocessing.Queue): 

            out_queues (Dict[str: multiprocessing.Queue]): Maps protocol to output assignment queue.


        """
        model = model_class(**model_kwargs)

        while not self.exit_event.is_set():
            try:
                data = in_queue.get(timeout=0.1)
                self.input_variables[data["pvname"]].value = data["value"]
                for protocol, queue in out_queues.items():
                    if protocol == data["protocol"]:
                        continue
                    queue.put(
                        {"input_variables":
                            [self.input_variables[data["pvname"]]]
                        }
                    )

                # update output variable state
                model_input = list(self.input_variables.values())
                predicted_output = model.evaluate(model_input)
                for protocol, queue in out_queues.items():
                    queue.put({"output_variables": predicted_output},
                              timeout=0.1)
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
                explicitely stopped using server.stop()

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
            
        if "pva" in self.protocols:
            self.pva_process.shutdown()

        logger.info("Server is stopped.")