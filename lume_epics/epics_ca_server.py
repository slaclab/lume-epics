import copy
import logging
import multiprocessing
import time
import signal
from typing import Dict
from lume_model.variables import Variable, InputVariable, OutputVariable
import numpy as np

import os
from queue import Full, Empty, Queue

from epics.ca import CAThread
import epics
from epics.multiproc import CAProcess

# initialize libca before pcaspy import
if not epics.ca.libca:
    epics.ca.initialize_libca()

from pcaspy import Driver, SimpleServer
from typing import Dict, Mapping, Union, List
from functools import partial


# Each server must have their outQueue in which the comm server will set the inputs and outputs vars to be updated
# Comm server must also provide one inQueue in which it will receive inputs from Servers

logger = logging.getLogger(__name__)


# Thread running server processing loop
class CAServerThread(CAThread):
    """
    A helper class to run server in a thread.
    """

    def __init__(self, server):
        """
        :param server: :class:`pcaspy.SimpleServer` object
        """
        super(CAThread, self).__init__()
        self.server = server
        self.running = True

    def run(self):
        """
        Start the server processing
        """
        while self.running:
            self.server.process(0.1)

    def stop(self):
        """
        Stop the server processing
        """
        self.running = False


class CAServer(CAProcess):
    """
    Process-based implementation of Channel Access server.

    Attributes:
        _ca_server (SimpleServer): pcaspy SimpleServer instance

        _ca_driver (Driver): pcaspy Driver instance

        _input_variables (Dict[str, InputVariable]): Mapping of input variable name to variable

        _ouptut_variables (Dict[str, InputVariable]): Mapping of output variable name to variable

        _server_thread (ServerThread): Thread for running the server

        shutdown_event (multiprocessing.Event): Event indicating shutdown

        exit_event (multiprocessing.Event): Event indicating early exit

        _running_indicator (multiprocessing.Value): Value indicating whether model execution ongoing

        _epics_config (dict): Dictionary describing EPICS configuration for model variables

        _in_queue (multiprocessing.Queue): Queue for pushing updated input variables to model execution

        _out_queue (multiprocessing.Queue): Process model output variables and sync with pvAccess server

    """

    protocol = "ca"

    def __init__(
        self,
        input_variables: Dict[str, InputVariable],
        output_variables: Dict[str, OutputVariable],
        epics_config: dict,
        in_queue: multiprocessing.Queue,
        out_queue: multiprocessing.Queue,
        running_indicator: multiprocessing.Value,
        *args,
        read_only: bool = False,
        **kwargs,
    ) -> None:
        """Initialize server process.

        Args:
            prefix (str): EPICS prefix for serving process variables

            input_variables (Dict[str, InputVariable]): Dictionary mapping pvname to lume-model input variable.

            output_variables (Dict[str, OutputVariable]):Dictionary mapping pvname to lume-model output variable.

            in_queue (multiprocessing.Queue): Queue for tracking updates to input variables

            out_queue (multiprocessing.Queue): Queue for tracking updates to output variables

        """
        super().__init__(*args, **kwargs)
        self._ca_server = None
        self._ca_driver = None
        self._server_thread = None
        self._input_variables = input_variables
        self._output_variables = output_variables
        self._in_queue = in_queue
        self._out_queue = out_queue
        self._providers = {}
        self._running_indicator = running_indicator
        self._epics_config = epics_config
        self.exit_event = multiprocessing.Event()
        self.shutdown_event = multiprocessing.Event()

        # utility maps
        self._pvname_to_varname_map = {
            config["pvname"]: var_name for var_name, config in epics_config.items()
        }
        self._varname_to_pvname_map = {
            var_name: config["pvname"] for var_name, config in epics_config.items()
        }

        # cached pv values
        self._cached_values = {}
        self._monitors = {}

    def update_pv(self, pvname, value) -> None:
        """Adds update to input process variable to the input queue.

        Args:
            pvname (str): Name of process variable

            value (Union[np.ndarray, float]): Value to set

        """
        self._cached_values.update({self._pvname_to_varname_map[pvname]: value})

        # only update if not running
        if not self._running_indicator.value:
            self._in_queue.put({"protocol": "ca", "pvs": self._cached_values})
            self._cached_values = {}

    def _monitor_callback(self, pvname=None, value=None, **kwargs) -> None:
        """Callback executed on value change events.s

        """
        self._cached_values.update({self._pvname_to_varname_map[pvname]: value})

        # only update if not running
        if not self._running_indicator.value:
            self._in_queue.put({"protocol": "ca", "pvs": self._cached_values})
            self._cached_values = {}

    def _initialize_model(self):
        """ Initialize model
        """
        self._in_queue.put(
            {
                "protocol": "ca",
                "pvs": {
                    var_name: var.value
                    for var_name, var in self._input_variables.items()
                },
            }
        )

    def setup_server(self) -> None:
        """Configure and start server.

        """
        # ignore interrupt in subprocess
        signal.signal(signal.SIGINT, signal.SIG_IGN)

        logger.info("Initializing CA server")

        # initialize channel access server
        self._ca_server = SimpleServer()

        # update value with stored defaults
        for var_name in self._input_variables:
            if self._epics_config[var_name]["serve"]:
                self._input_variables[var_name].value = self._input_variables[
                    var_name
                ].default

            else:
                val = epics.caget(self._varname_to_pvname_map[var_name])
                if not val:
                    self.exit_event.set()
                    raise ValueError(
                        f"Unable to connect to {self._varname_to_pvname_map[var_name]}"
                    )

                self._input_variables[var_name].value = val

        # update output variable values
        self._initialize_model()
        model_outputs = self._out_queue.get()
        for output in model_outputs["output_variables"]:
            self._output_variables[output.name] = output

        # differentiate between values to serve and not to serve
        to_serve = []
        external = []
        variables = copy.deepcopy(self._input_variables)
        variables.update(self._output_variables)
        for var in variables:
            if self._epics_config[var]["serve"]:
                to_serve.append(var)

            else:
                external.append(var)

        # build pvdb and child to parent map for area detector scheme
        pvdb, self._child_to_parent_map = build_pvdb(
            [variables[var_name] for var_name in to_serve], self._epics_config
        )

        # for external variables create monitors
        for var_name in external:
            self._monitors[var_name] = epics.pv.get_pv(
                self._varname_to_pvname_map[var_name]
            )
            self._monitors[var_name].add_callback(self._monitor_callback)

        # Register pvs with server
        self._ca_server.createPV("", pvdb)

        # set up driver for handing read and write requests to process variables
        self._ca_driver = CADriver(server=self)

        # start the server thread
        self._server_thread = CAServerThread(self._ca_server)
        self._server_thread.start()

        logger.info("CA server started")

    def update_pvs(
        self,
        input_variables: List[InputVariable],
        output_variables: List[OutputVariable],
    ):
        """Update process variables over Channel Access.

        Args:
            input_variables (List[InputVariable]): List of lume-epics output variables.

            output_variables (List[OutputVariable]): List of lume-model output variables.

        """
        variables = input_variables + output_variables

        self._ca_driver.update_pvs(variables)

    def run(self) -> None:
        """Start server process.

        """
        self.setup_server()
        while not self.shutdown_event.is_set():
            try:
                data = self._out_queue.get_nowait()
                inputs = data.get("input_variables", [])
                outputs = data.get("output_variables", [])
                self.update_pvs(inputs, outputs)

            except Empty:
                time.sleep(0.05)
                logger.debug("out queue empty")

        self._server_thread.stop()
        logger.info("Channel access server stopped.")

    def shutdown(self):
        """Safely shutdown the server process.

        """
        self.shutdown_event.set()


def build_pvdb(variables: List[Variable], epics_config: dict) -> tuple:
    """Utility function for building dictionary (pvdb) used to initialize the channel
    access server.

    Args:
        variables (List[Variable]): List of lume_model variables to be served with
            channel access server.

        epics_config (dict): Epics pvnames for each variable

    Returns:
        pvdb (dict)
        child_to_parent_map (dict): Mapping of child pvs to parent model variables

    """
    pvdb = {}
    child_to_parent_map = {}

    for variable in variables:
        pvname = epics_config.get(variable.name)["pvname"]
        if variable.variable_type == "image":

            if variable.value is None:
                ndim = np.nan
                shape = np.nan
                array_size_x = np.nan
                array_size_y = np.nan
                array_size = np.nan
                array_data = np.nan
                count = np.nan

            else:
                ndim = variable.value.ndim
                shape = variable.value.shape
                array_size_x = variable.value.shape[0]
                array_size_y = variable.value.shape[1]
                array_size = int(np.prod(variable.value.shape))
                array_data = variable.value.flatten()
                count = int(np.prod(variable.value.shape))

            # infer color mode
            if ndim == 2:
                color_mode = 0

            elif ndim == 3:
                color_mode = 1

            else:
                logger.info("Color mode cannot be inferred from image shape %s.", ndim)
                color_mode = np.nan

            # assign default PVS
            pvdb.update(
                {
                    f"{pvname}:NDimensions_RBV": {
                        "type": "float",
                        "prec": variable.precision,
                        "value": ndim,
                    },
                    f"{pvname}:Dimensions_RBV": {
                        "type": "int",
                        "prec": variable.precision,
                        "count": ndim,
                        "value": shape,
                    },
                    f"{pvname}:ArraySizeX_RBV": {"type": "int", "value": array_size_x,},
                    f"{pvname}:ArraySizeY_RBV": {"type": "int", "value": array_size_y,},
                    f"{pvname}:ArraySize_RBV": {"type": "int", "value": array_size,},
                    f"{pvname}:ArrayData_RBV": {
                        "type": "float",
                        "prec": variable.precision,
                        "count": count,
                        "value": array_data,
                    },
                    f"{pvname}:MinX_RBV": {"type": "float", "value": variable.x_min,},
                    f"{pvname}:MinY_RBV": {"type": "float", "value": variable.y_min,},
                    f"{pvname}:MaxX_RBV": {"type": "float", "value": variable.x_max,},
                    f"{pvname}:MaxY_RBV": {"type": "float", "value": variable.y_max,},
                    f"{pvname}:ColorMode_RBV": {"type": "int", "value": color_mode,},
                }
            )

            child_to_parent_map.update(
                {
                    f"{pvname}:{child}": variable.name
                    for child in [
                        "NDimensions_RBV",
                        "Dimensions_RBV",
                        "ArraySizeX_RBV",
                        "ArraySizeY_RBV",
                        "ArraySize_RBV",
                        "ArrayData_RBV",
                        "MinX_RBV",
                        "MinY_RBV",
                        "MaxX_RBV",
                        "MaxY_RBV",
                        "ColorMode_RBV",
                    ]
                }
            )

            if "units" in variable.__fields_set__:
                pvdb[f"{pvname}:ArrayData_RBV"]["unit"] = variable.units

            # handle rgb arrays
            if ndim > 2:
                pvdb[f"{pvname}:ArraySizeZ_RBV"] = {
                    "type": "int",
                    "value": variable.value.shape[2],
                }

        elif variable.variable_type == "scalar":
            pvdb[pvname] = variable.dict(exclude_unset=True, by_alias=True)
            if variable.value_range is not None:
                pvdb[pvname]["hilim"] = variable.value_range[1]
                pvdb[pvname]["lolim"] = variable.value_range[0]

            if variable.units is not None:
                pvdb[pvname]["unit"] = variable.units

        elif variable.variable_type == "array":

            # assign default PVS
            pvdb.update(
                {
                    f"{pvname}:NDimensions_RBV": {
                        "type": "float",
                        "prec": variable.precision,
                        "value": variable.value.ndim,
                    },
                    f"{pvname}:Dimensions_RBV": {
                        "type": "int",
                        "prec": variable.precision,
                        "count": variable.value.ndim,
                        "value": variable.value.shape,
                    },
                    f"{pvname}:ArrayData_RBV": {
                        "type": variable.value_type,
                        "prec": variable.precision,
                        "count": int(np.prod(variable.value.shape)),
                        "value": variable.value.flatten(),
                    },
                    f"{pvname}:ArraySize_RBV": {
                        "type": "int",
                        "value": int(np.prod(variable.value.shape)),
                    },
                }
            )

            child_to_parent_map.update(
                {
                    f"{pvname}:{child}": variable.name
                    for child in [
                        "NDimensions_RBV",
                        "Dimensions_RBV",
                        "ArraySize_RBV",
                        "ArrayData_RBV",
                    ]
                }
            )

            if "units" in variable.__fields_set__:
                pvdb[f"{pvname}:ArrayData_RBV"]["unit"] = variable.units

    return pvdb, child_to_parent_map


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

        # handle area detector types
        model_var_name = self.server._pvname_to_varname_map.get(pvname)

        if pvname in self.server._child_to_parent_map:
            model_var_name = self.server._child_to_parent_map[pvname]

        if model_var_name in self.server._output_variables:
            logger.warning(
                "Cannot update variable %s. Output variables can only be updated via surrogate model callback.",
                pvname,
            )
            return False

        if value is None:
            logger.debug(f"None value provided for {pvname}")
            return False

        if model_var_name in self.server._input_variables:

            if self.server._input_variables[model_var_name].is_constant:
                logger.debug("Unable to update constant variable %s", model_var_name)

            else:
                self.setParam(pvname, value)
                self.updatePVs()
                logger.debug(
                    "Channel Access process variable %s updated with value %s",
                    pvname,
                    value,
                )

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
            pvname = self.server._varname_to_pvname_map[variable.name]
            if variable.name in self.server._input_variables and variable.is_constant:
                logger.debug(
                    "Cannot update constant variable %s, %s", variable.name, pvname
                )

            else:
                if variable.variable_type == "image":
                    logger.debug(
                        "Channel Access image process variable %s updated.", pvname,
                    )
                    self.setParam(pvname + ":ArrayData_RBV", variable.value.flatten())
                    self.setParam(pvname + ":MinX_RBV", variable.x_min)
                    self.setParam(pvname + ":MinY_RBV", variable.y_min)
                    self.setParam(pvname + ":MaxX_RBV", variable.x_max)
                    self.setParam(pvname + ":MaxY_RBV", variable.y_max)

                elif variable.variable_type == "scalar":
                    logger.debug(
                        "Channel Access process variable %s updated wth value %s.",
                        pvname,
                        variable.value,
                    )
                    self.setParam(pvname, variable.value)

                elif variable.variable_type == "array":
                    logger.debug(
                        "Channel Access image process variable %s updated.", pvname,
                    )

                    self.setParam(pvname + ":ArrayData_RBV", variable.value.flatten())

                else:
                    logger.debug(
                        "No instructions for handling variable %s of type %s",
                        variable.name,
                        variable.variable_type,
                    )

        self.updatePVs()
