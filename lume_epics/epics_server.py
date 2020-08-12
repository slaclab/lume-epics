"""
This module contains the EPICS server class along with the associated pvAccess and 
Channel Acccess infrastructure. Included is the Channel Access driver, handlers for 
pvAccess callbacks, and associated utilities. The Server may be optionally initialized
to use only one protocol, using both by default.

"""

import copy
import numpy as np
import time
import logging 
import threading
from queue import Queue, Empty, Full

from threading import Thread, Event, local
from typing import Dict, Mapping, Union, List

from pcaspy import Driver, SimpleServer

from p4p.nt import NTScalar, NTNDArray
from p4p.server.thread import SharedPV
from p4p.server import Server as P4PServer
from p4p.nt.ndarray import ntndarray as NTNDArrayData
from p4p.server.raw import ServOpWrap

from lume_model.variables import Variable, InputVariable, OutputVariable
from lume_model.models import SurrogateModel

logger = logging.getLogger(__name__)


comm_queue = Queue(maxsize=5)
pva_queue = Queue(maxsize=10)
ca_queue = Queue(maxsize=10)



def add_to_comm_queue(put_data):
    # check if queue full
    if comm_queue.full():
        logger.debug("Clearing queue")
        for i in range(comm_queue.maxsize):
            try:
                oldest_data = comm_queue.get_nowait()
                comm_queue.task_done()
            except Empty:
                pass

    try:
        comm_queue.put(put_data, timeout=0.1)
    except Full:
        logger.error("Communication queue is still full.")
        


def build_pvdb(input_variables: List[Variable], output_variables: List[Variable]) -> dict:
    """Utility function for building dictionary (pvdb) used to initialize the channel
    access server.
    
    Args:
        input_variables (List[Variable]): List of lume_model variables to be served with
            channel access server.

        output_variables (List[Variable]): List of lume_model variables to be served with
            channel access server.

    """
    pvdb = {}

    # convert to list
    variables = copy.deepcopy(input_variables)
    variables.update(output_variables)
    variables = list(variables.values())

    for variable in variables:
        if variable.variable_type == "image":

            # infer color mode
            if variable.value.ndim == 2:
                color_mode = 0

            elif variable.value:
                raise Exception("Color mode cannot be inferred from image shape.")

            # assign default PVS
            pvdb.update(
                {
                    f"{variable.name}:NDimensions_RBV": {
                        "type": "float",
                        "prec": variable.precision,
                        "value": variable.value.ndim,
                    },
                    f"{variable.name}:Dimensions_RBV": {
                        "type": "int",
                        "prec": variable.precision,
                        "count": variable.value.ndim,
                        "value": variable.value.shape,
                    },
                    f"{variable.name}:ArraySizeX_RBV": {
                        "type": "int",
                        "value": variable.value.shape[0],
                    },
                    f"{variable.name}:ArraySizeY_RBV": {
                        "type": "int",
                        "value": variable.value.shape[1],
                    },
                    f"{variable.name}:ArraySize_RBV": {
                        "type": "int",
                        "value": int(np.prod(variable.value.shape)),
                    },
                    f"{variable.name}:ArrayData_RBV": {
                        "type": "float",
                        "prec": variable.precision,
                        "count": int(np.prod(variable.value.shape)),
                        "value": variable.value,
                        #   "units": variable.units,
                    },
                    f"{variable.name}:MinX_RBV": {
                        "type": "float",
                        "value": variable.x_min,
                    },
                    f"{variable.name}:MinY_RBV": {
                        "type": "float",
                        "value": variable.y_min,
                    },
                    f"{variable.name}:MaxX_RBV": {
                        "type": "float",
                        "value": variable.x_max,
                    },
                    f"{variable.name}:MaxY_RBV": {
                        "type": "float",
                        "value": variable.y_max,
                    },
                    f"{variable.name}:ColorMode_RBV": {
                        "type": "int",
                        "value": color_mode,
                    },
                }
            )

            if "units" in variable.__fields_set__:
                pvdb[f"{variable.name}:ArrayData_RBV"]["unit"] = variable.units

            # placeholder for color images, not yet implemented
            if variable.value.ndim > 2:
                pvdb[f"{variable.name}:ArraySizeZ_RBV"] = {
                    "type": "int",
                    "value": variable.value.shape[2],
                }

        else:
            pvdb[variable.name] = variable.dict(
                exclude_unset=True, by_alias=True
            )
            if variable.value_range is not None:
                pvdb[variable.name]["hilim"] = variable.value_range[1]
                pvdb[variable.name]["lolim"] = variable.value_range[0]

            if variable.units is not None:
                pvdb[variable.name]["unit"] = variable.units

    return pvdb


class CADriver(Driver):
    """
    Class for handling read and write requests to Channel Access process variables.

    Attributes:
        input_variables (List[Variable]): List of lume-model variables to use as 
            inputs.

        ouput_variables (List[Variable]): List of lume-model variables to use as 
            outputs.

    """

    def __init__(
        self, input_variables: Dict[str, Variable], output_variables: Dict[str, Variable],
    ) -> None:
        """Initialize the Channel Access driver. Store input state and output state.

        Args:
            input_variables (Dict[str, Variable]): Dict of lume-model variables to use as model inputs.

            ouput_variables (Dict[str, Variable]): Dict of lume-model variables to use as model outputs.

        """

        super(CADriver, self).__init__()
        self.input_variables =  input_variables
        self.output_variables = output_variables

    def read(self, pvname: str) -> Union[float, np.ndarray]:
        """Method executed by server when clients read a Channel Access process 
        variable.

        Args:
            pvname (str): Process variable name.

        """
        return self.getParam(pvname)

    def write(self, pvname: str, value: Union[float, np.ndarray]) -> bool:
        """Method executed by server when clients write to a Channel Access process
        variable.


        Args:
            pvname (str): Process variable name.

            value (Union[float, np.ndarray]): Value to assign to the process variable.

        """
        if pvname in self.output_variables:
            logger.warning("Cannot update variable %s. Output variables can only be updated via surrogate model callback.", pvname)
            return False


        if pvname in self.input_variables:
            self.input_variables[pvname].value = value
            self.setParam(pvname, value)
            self.updatePVs()
            logger.debug("Channel Access process variable %s updated with value %s", pvname, value)

            # add updated input to the queue
            add_to_comm_queue({"protocol": "ca","pvname": pvname, "value": value})
            return True

        else:
            logger.error("%s not found in server variables.", pvame)
            return False


    def set_output_pvs(self, output_variables: List[Variable]) -> None:
        """Update output Channel Access process variables after model execution.

        Args:
            output_variables (List[Variable]): List of output variables.
        """
        for variable in output_variables:
            if variable.variable_type == "image":
                logger.debug("Channel Access image process variable %s updated.", variable.name)
                self.setParam(
                    variable.name + ":ArrayData_RBV", variable.value.flatten()
                )
                self.setParam(variable.name + ":MinX_RBV", variable.x_min)
                self.setParam(variable.name + ":MinY_RBV", variable.y_min)
                self.setParam(variable.name + ":MaxX_RBV", variable.x_max)
                self.setParam(variable.name + ":MaxY_RBV", variable.y_max)

            else:
                logger.debug("Channel Access process variable %s updated wth value %s.", variable.name, variable.value)
                self.setParam(variable.name, variable.value)

        self.updatePVs()


class PVAccessInputHandler:
    """Handler object that defines the callbacks to execute on put operations to input
    process variables.
    """

    def __init__(self, prefix: str):
        """
        Initialize the handler with prefix and image pv attributes

        Args:
            prefix (str): Prefix used to format process variables

        """
        self.prefix = prefix

    def put(self, pv: SharedPV, op: ServOpWrap) -> None:
        """Updates the global input process variable state, posts the input process 
        variable value change, runs the thread local OnlineSurrogateModel instance 
        using the updated global input process variable states, and posts the model 
        output values to the output process variables.

        Args:
            pv (SharedPV): Input process variable on which the put operates.

            op (ServOpWrap): Server operation initiated by the put call.

        """
        global providers
        global input_pvs

        # update input values and global input process variable state
        pv.post(op.value())
        input_pvs[op.name().replace(f"{self.prefix}:", "")].value = op.value()
        pvname = input_pvs[op.name().replace(f"{self.prefix}:", "")].name

        add_to_comm_queue({"protocol": "pva","pvname": pvname, "value": op.value()})

        # mark server operation as complete
        op.done()


def set_pva_outputs(output_variables, prefix):
    """
    Function for setting outputs over pva

    """

    for variable in output_variables:
        if variable.variable_type == "image":
            logger.debug("pvAccess image process variable %s updated.", variable.name)
            nd_array = variable.value.view(NTNDArrayData)

            # get dw and dh from model output
            nd_array.attrib = {
                "x_min": variable.x_min,
                "y_min": variable.y_min,
                "x_max": variable.x_max,
                "y_max": variable.y_max,
            }

            output_provider = providers[f"{prefix}:{variable.name}"]
            output_provider.post(nd_array)

        # do not build attribute pvs
        else:
            logger.debug("pvAccess process variable %s updated with value %s.", variable.name, variable.value)
            output_provider = providers[f"{prefix}:{variable.name}"]
            output_provider.post(variable.value)


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
        protocols: List[str] = ["ca", "pva"],
        model_port: int = 5000,
        model_kwargs: dict = {},
    ) -> None:
        """Create OnlineSurrogateModel instance in the main thread and initialize output 
        variables by running with the input process variable state, input/output 
        variable tracking, start the server, create the process variables, and start 
        the driver.

        Args:
            model_class (SurrogateModel): Surrogate model class to be instantiated.

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
                'Invalid protocol provided. Protocol options are "pva" (pvAccess) and "ca" (Channel Access).'
            )

        # need these to be global to access from threads
        global providers
        global input_pvs
        global output_pvs
        global _model_address
        self.prefix = prefix
        self.protocols = protocols

        providers = {}
        input_pvs = input_variables
        output_pvs = output_variables

        self.input_variables = input_variables
        self.output_variables = output_variables

        # update inputs for starting value to be the default
        for variable in self.input_variables.values():
            if variable.value is None:
                variable.value = variable.default

       # model_thread = threading.Thread(target=flask_model_thread, args=(model_class, model_port), kwargs={"model_kwargs": model_kwargs})
        # model_thread.start()
        self.comm_thread = threading.Thread(target=self.run_comm_thread, args = (model_class,), kwargs={"model_kwargs": model_kwargs})
        self.ca_thread = threading.Thread(target=self.run_ca_server)
        self.pva_thread = threading.Thread(target=self.run_pva_server)
        


        model = model_class(**model_kwargs) 
        self.output_variables = model.evaluate(self.input_variables)
        self.output_variables = {variable.name: variable for variable in self.output_variables}

        # get starting output from the model and set up output process variables
      #  self.output_variables = run_model(input_variables, output_variables)

        #if "pva" in self.protocols:
       #     self.initialize_pva_server()


    def run_comm_thread(self, model_class, model_kwargs={}):
        model = model_class(**model_kwargs)

        while True:
            try:
                data = comm_queue.get(timeout=0.1)
                self.input_variables[data["pvname"]].value = data["value"]
                # update output variable state

                # UPDATE COMPLEMENTARY INPUT


                predicted_output = model.evaluate(self.input_variables)
                pva_queue.put(predicted_output, timeout=0.1)
                ca_queue.put(predicted_output, timeout=0.1)
                comm_queue.task_done()
            except Empty:
                continue
            except Full:
                print("PVA or CA full")
    

    def run_ca_server(self) -> None:
        """Initialize the Channel Access server and driver. Sets the initial
        output variable values.
        """
        # initialize channel access server
        self.ca_server = SimpleServer()

        # create all process variables using the process variables stored in pvdb
        # with the given prefix
        pvdb = build_pvdb(self.input_variables, self.output_variables)
        self.ca_server.createPV(self.prefix + ":", pvdb)

        # set up driver for handing read and write requests to process variables
        self.ca_driver = CADriver(self.input_variables, self.output_variables)
        self.ca_driver.set_output_pvs(list(self.output_variables.values()))

        while True:
            self.ca_server.process(0.1)
            try:
                data = ca_queue.get(False)
                self.ca_driver.set_output_pvs(data)
                ca_queue.task_done()
            except Empty:
                pass

    def run_pva_server(self) -> None:
        pva_worker_queue = WorkQueue()
        logger.info("Initializing pvAccess server")
        # initialize global inputs
        for variable in self.input_variables.values():
            # input_pvs[variable.name] = variable.value
            pvname = f"{self.prefix}:{variable.name}"

            # prepare scalar variable types
            if variable.variable_type == "scalar":
                pv = SharedPV(
                    handler=PVAccessInputHandler(
                        self.prefix
                    ),  # Use PVAccessInputHandler class to handle callbacks
                    nt=NTScalar("d"),
                    initial=variable.value,
                    queue = pva_worker_queue
                )

            # prepare image variable types
            elif variable.variable_type == "image":
                nd_array = variable.value.view(NTNDArrayData)

                nd_array.attrib = {
                    "x_min": variable.x_min,
                    "y_min": variable.y_min,
                    "x_max": variable.x_max,
                    "y_max": variable.y_max,
                }

                pv = SharedPV(
                    handler=PVAccessInputHandler(
                        self.prefix
                    ),  # Use PVAccessInputHandler class to handle callbacks
                    nt=NTNDArray(),
                    initial=nd_array,
                    queue = pva_worker_queue
                )

            else:
                raise ValueError(
                    "Unsupported variable type provided: %s", variable.variable_type
                )

            providers[pvname] = pv

        # use default handler for the output process variables
        # updates to output pvs are handled from post calls within the input update
        for variable in self.output_variables.values():
            pvname = f"{self.prefix}:{variable.name}"
            if variable.variable_type == "scalar":
                pv = SharedPV(nt=NTScalar(), initial=variable.value, queue = pva_queue)

            elif variable.variable_type == "image":

                nd_array = variable.value.view(NTNDArrayData)

                # get limits from model output
                nd_array.attrib = {
                    "x_min": np.float64(variable.x_min),
                    "y_min": np.float64(variable.y_min),
                    "x_max": np.float64(variable.x_max),
                    "y_max": np.float64(variable.y_max),
                }

                pv = SharedPV(nt=NTNDArray(), initial=nd_array, queue = pva_worker_queue)

            else:
                raise ValueError(
                    "Unsupported variable type provided: %s", variable.variable_type
                )

            providers[pvname] = pv

        else:
            pass  # throw exception for incorrect data type


        self.pva_server = P4PServer(providers=[providers])
        while True:
            try:
                task = pva_worker_queue.handle()
                data = pva_queue.get_nowait()
                set_pva_outputs(data, self.prefix)
                pva_queue.task_done()
            except Empty:
                logger.debug("pva worker or pva queue empty")

        logger.info("pvAccess server started")                


    def start(self, monitor: bool = True) -> None:
        """Starts server using set server protocol(s).

        Args: 
            monitor (bool): Indicates whether to run the server in the background
                or to continually monitor. If monitor = False, the server must be
                explicitely stopped using server.stop()

        """

        # set up exit event for threads
        self.exit_event = Event()
        self.comm_thread.start()

        if "ca" in self.protocols:
            self.ca_thread.start()

        if "pva" in self.protocols:
            self.pva_thread.start()


    #    if monitor:
    #        try:
    #            while True:
                   # if "ca" in self.protocols:
                   #     self.ca_server.process(0.1)
    #                else:
    #                    time.sleep(0.1)

    #        except KeyboardInterrupt:
    #            logger.info("Stopping servers")
    #            if "ca" in self.protocols:
    #                self.ca_driver.exit_event.set()

    #            if "pva" in self.protocols:
    #                self.pva_server.stop()

    def stop(self) -> None:
        """Stops the server.

        """
        logger.info("Stopping server.")

        if "ca" in self.protocols:
            self.ca_driver.exit_event.set()

        if "pva" in self.protocols:
            self.pva_server.stop()



class WorkQueue(object):

    """A threaded work queue.
    """
    _stopit = object()

    def __init__(self, maxsize=5):
        self._Q = Queue(maxsize=0)

    def push(self, callable):
        self._Q.put_nowait(callable)  # throws Queue.Full

    def push_wait(self, callable):
        self._Q.put(callable)

    def interrupt(self):
        """Break one call to handle()
        eg. Call N times to break N threads.
        This call blocks if the queue is full.
        """
        self._Q.put(self._stopit)


    def handle(self):
        if not self._Q.empty():
            to_process = self._Q.qsize()
            for i in range(to_process):
                try:
                    callable = None
                    callable = self._Q.get(True, 0.1)
                except Empty:
                    continue
                try:
                    callable()
                    self._Q.task_done()
                except:
                    # add logging
                    pass

    def handle_old(self):
        """Process queued work until interrupt() is called
        """
        while True:
            # TODO: Queue.get() (and anything using thread.allocate_lock
            #       ignores signals :(  so timeout periodically to allow delivery
            try:
                callable = None # ensure no lingering references to past work while blocking
                callable = self._Q.get(True, 1.0)
            except Empty:
                continue  # retry on timeout
            try:
                print(callable)
                if callable is self._stopit:
                    break
                callable()
            except:
                _log.exception("Error from WorkQueue")
            finally:
                self._Q.task_done()