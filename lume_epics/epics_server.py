"""
This module contains the EPICS server class along with the associated pvAccess and 
Channel Acccess infrastructure. Included is the Channel Access driver, handlers for 
pvAccess callbacks, and associated utilities. The Server may be optionally initialized
to use only one protocol, using both by default.

"""

import time
import logging
import threading
import multiprocessing

from threading import Thread, Event, local
from typing import Dict, Mapping, Union, List
from queue import Full, Empty

from lume_model.variables import Variable, InputVariable, OutputVariable
from lume_model.models import SurrogateModel
from .epics_pva_server import PVAServer

logger = logging.getLogger(__name__)


# def add_to_comm_queue(put_data):
#     # check if queue full
#     if comm_queue.full():
#         print('********** COMM QUEUE IS FULL **********')
#         logger.debug("Clearing queue")
#         for i in range(comm_queue.maxsize):
#             try:
#                 oldest_data = comm_queue.get_nowait()
#                 comm_queue.task_done()
#             except Empty:
#                 pass
#
#     try:
#         comm_queue.put(put_data, timeout=0.1)
#     except Full:
#         logger.error("Communication queue is still full.")


class Server:
    """
    Server for EPICS process variables. Can be optionally initialized with only
    pvAccess or Channel Access protocols; but, defaults to serving over both. 

    Attributes:
        model (OnlineSurrogateModel): OnlineSurrogateModel instance used for getting
            predictions.

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
        protocols: List[str] = ["pva"],
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
        self.output_variables = model.evaluate(self.input_variables)
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

        # self.ca_thread = threading.Thread(target=self.run_ca_server)
        self.pva_process = PVAServer(
            prefix=self.prefix,
            input_variables=self.input_variables,
            output_variables=self.output_variables,
            in_queue=self.in_queue,
            out_queue=self.out_queues["pva"]
        )

    def run_comm_thread(self, model_class, model_kwargs={}, in_queue=None,
                        out_queues=None):
        model = model_class(**model_kwargs)

        while not self.exit_event.is_set():
            try:
                data = in_queue.get(timeout=0.1)
                self.input_variables[data["pvname"]].value = data["value"]
                for protocol, queue in out_queues.items():
                    if protocol == data["protocol"]:
                        continue
                    print('Server is updating out queue for: ', protocol, ' with: ', data["pvname"])
                    queue.put(
                        {"input_variables":
                            [self.input_variables[data["pvname"]]]
                        }
                    )
                # update output variable state

                # UPDATE COMPLEMENTARY INPUT
                print('Model evaluate called')
                predicted_output = model.evaluate(self.input_variables)
                print('Model evaluate finished')
                print('Predicted Output: ', predicted_output)
                # in_queue.task_done()
                for _, queue in out_queues.items():
                    queue.put({"output_variables": predicted_output},
                              timeout=0.1)
            except Empty:
                continue
            except Full:
                print(f"Queue is Full -> CA or PVA")
    #
    # def run_ca_server(self) -> None:
    #     """Initialize the Channel Access server and driver. Sets the initial
    #     output variable values.
    #     """
    #     # initialize channel access server
    #     self.ca_server = SimpleServer()
    #
    #     # create all process variables using the process variables stored in pvdb
    #     # with the given prefix
    #     pvdb = build_pvdb(self.input_variables, self.output_variables)
    #     self.ca_server.createPV(self.prefix + ":", pvdb)
    #
    #     # set up driver for handing read and write requests to process variables
    #     self.ca_driver = CADriver(self.input_variables, self.output_variables)
    #     self.ca_driver.set_output_pvs(list(self.output_variables.values()))
    #
    #     while True:
    #         self.ca_server.process(0.1)
    #         try:
    #             data = ca_queue.get(False)
    #             self.ca_driver.set_output_pvs(data)
    #             ca_queue.task_done()
    #         except Empty:
    #             time.sleep(0.01)
    #             pass

    def start(self, monitor: bool = True) -> None:
        """Starts server using set server protocol(s).

        Args: 
            monitor (bool): Indicates whether to run the server in the background
                or to continually monitor. If monitor = False, the server must be
                explicitely stopped using server.stop()

        """
        self.comm_thread.start()

        # if "ca" in self.protocols:
        #     self.ca_process.start()

        if "pva" in self.protocols:
            self.pva_process.start()

    def stop(self) -> None:
        """Stops the server.

        """
        logger.info("Stopping server.")
        self.exit_event.set()

        # if "ca" in self.protocols:
        #     self.ca_driver.exit_event.set()

        if "pva" in self.protocols:
            self.pva_process.terminate()
            # self.pva_server.stop()

