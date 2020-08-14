import copy
import logging
import multiprocessing
import time
import signal 
from typing import Dict

from lume_model.variables import Variable, InputVariable, OutputVariable
import numpy as np
from pcaspy import Driver, SimpleServer
from pcaspy.tools import ServerThread
from queue import Full, Empty, Queue

from typing import Dict, Mapping, Union, List

# Each server must have their outQueue in which the comm server will set the inputs and outputs vars to be updated
# Comm server must also provide one inQueue in which it will receive inputs from Servers

logger = logging.getLogger(__name__)


class CAServer(multiprocessing.Process):
    """
    Process-based implementation of Channel Access server.

    Attributes:
        ca_server (SimpleServer): pcaspy SimpleServer instance

        ca_driver (Driver): pcaspy Driver instance

        server_thread (ServerThread): Thread for running the server

        exit_event (multiprocessing.Event): Event indicating shutdown

    """
    protocol = "ca"

    def __init__(self,
                 prefix: str,
                 input_variables: Dict[str, InputVariable], 
                 output_variables: Dict[str, OutputVariable],
                 in_queue: multiprocessing.Queue, 
                 out_queue: multiprocessing.Queue, *args, **kwargs) -> None:
        """Initialize server process.

        Args:
            prefix (str): EPICS prefix for serving process variables

            input_variables (Dict[str, InputVariable]): Dictionary mapping pvname to lume-model input variable.

            output_variables (Dict[str, OutputVariable]):Dictionary mapping pvname to lume-model output variable.

            in_queue (multiprocessing.Queue): Queue for tracking updates to input variables

            out_queue (multiprocessing.Queue): Queue for tracking updates to output variables

        """
        super().__init__(*args, **kwargs)
        self._prefix = prefix
        self._input_variables = input_variables
        self._output_variables = output_variables
        self._in_queue = in_queue
        self._out_queue = out_queue
        self._providers = {}
        self.ca_server = None
        self.ca_driver = None
        self.server_thread = None
        self.exit_event = multiprocessing.Event()

    def update_pv(self, pvname, value) -> None:
        """Adds update to input process variable to the input queue.

        Args:
            pvname (str): Name of process variable

            value (Union[np.ndarray, float]): Value to set 

        """
        val = value
        pvname = pvname.replace(f"{self._prefix}:", "")
        self._in_queue.put(
            {"protocol": self.protocol, "pvname": pvname, "value": val}
        )

    def setup_server(self) -> None:
        """Configure and start server.

        """
        # ignore interrupt in subprocess
        signal.signal(signal.SIGINT, signal.SIG_IGN)

        logger.info("Initializing CA server")

        # initialize channel access server
        self.ca_server = SimpleServer()

        # create all process variables using the process variables stored in
        # pvdb with the given prefix
        pvdb = build_pvdb(self._input_variables, self._output_variables)
        self.ca_server.createPV(self._prefix + ":", pvdb)

        # set up driver for handing read and write requests to process variables
        self.ca_driver = CADriver(server=self)

        # start the server thread
        self.server_thread = ServerThread(self.ca_server)
        self.server_thread.start()

        logger.info("CA server started")

    def update_pvs(self, input_variables: List[InputVariable], output_variables: List[OutputVariable]):
        """Update process variables over Channel Access.

        Args:
            input_variables (List[InputVariable]): List of lume-epics output variables.

            output_variables (List[OutputVariable]): List of lume-model output variables.

        """
        variables = input_variables + output_variables
        self.ca_driver.update_pvs(variables)

    def run(self) -> None:
        """Start server process.

        """
        self.setup_server()
        while not self.exit_event.is_set():
            try:
                data = self._out_queue.get_nowait()
                inputs = data.get('input_variables', [])
                outputs = data.get('output_variables', [])
                self.update_pvs(inputs, outputs)
            except Empty:
                time.sleep(0.01)
                logger.debug("out queue empty")

        self.server_thread.stop()
        logger.info("Channel access server stopped.")

    def shutdown(self):
        """Safely shutdown the server process. 

        """
        self.exit_event.set()


def build_pvdb(input_variables: List[InputVariable],
               output_variables: List[OutputVariable]) -> dict:
    """Utility function for building dictionary (pvdb) used to initialize the channel
    access server.

    Args:
        input_variables (List[InputVariable]): List of lume_model input variables to be served with
            channel access server.

        output_variables (List[OutputVariable]): List of lume_model output variables to be served with
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
                raise Exception(
                    "Color mode cannot be inferred from image shape.")

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
    """

    def __init__(self, server) -> None:
        """Initialize the Channel Access driver. Store input state and output state.

        """
        super(CADriver, self).__init__()
        self.server = server

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
        if pvname in self.server._output_variables:
            logger.warning(
                "Cannot update variable %s. Output variables can only be updated via surrogate model callback.",
                pvname)
            return False

        if pvname in self.server._input_variables:
            self.setParam(pvname, value)
            self.updatePVs()
            logger.debug(
                "Channel Access process variable %s updated with value %s",
                pvname, value)

            self.server.update_pv(pvname=pvname, value=value)
            return True

        else:
            logger.error("%s not found in server variables.", pvname)
            return False

    def update_pvs(self, variables: List[Variable]) -> None:
        """Update output Channel Access process variables after model execution.

        Args:
            variables (List[Variable]): List of variables.
        """
        for variable in variables:
            if variable.variable_type == "image":
                logger.debug(
                    "Channel Access image process variable %s updated.",
                    variable.name)
                self.setParam(
                    variable.name + ":ArrayData_RBV", variable.value.flatten()
                )
                self.setParam(variable.name + ":MinX_RBV", variable.x_min)
                self.setParam(variable.name + ":MinY_RBV", variable.y_min)
                self.setParam(variable.name + ":MaxX_RBV", variable.x_max)
                self.setParam(variable.name + ":MaxY_RBV", variable.y_max)

            else:
                logger.debug(
                    "Channel Access process variable %s updated wth value %s.",
                    variable.name, variable.value)
                self.setParam(variable.name, variable.value)

        self.updatePVs()
