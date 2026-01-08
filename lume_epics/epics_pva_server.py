import logging
import copy
import multiprocessing
from multiprocessing.managers import DictProxy
from multiprocessing.sharedctypes import Synchronized
from queue import Full, Empty
from lume_epics import model, types
import numpy as np
import time
import signal
import math
from typing import List, Union, Any, Tuple
from functools import partial
from typing import Dict
from lume_model.variables import Variable, ScalarVariable
from p4p.client.thread import Context
from p4p.nt import NTScalar, NTNDArray, NTTable
from p4p.server.thread import SharedPV
from p4p.server import Server as P4PServer
from p4p.nt.ndarray import ntndarray as NTNDArrayData
from p4p.server.raw import ServOpWrap
from p4p import Value, Type
from lume_epics.types import type_handler

p4p_logger = logging.getLogger("p4p")
p4p_logger.setLevel("DEBUG")
# Each server must have their outQueue in which the comm server will set the inputs and outputs vars to be updated
# Comm server must also provide one inQueue in which it will receive inputs from Servers

logger = logging.getLogger(__name__)
logger.setLevel(logging.DEBUG)

class PVAServer(multiprocessing.Process):
    """
    Process-based implementation of Channel Access server.

    Attributes:
        pva_server (P4PServer): p4p server instance
        exit_event (multiprocessing.Event): Event indicating pvAccess server error and communicating to main
        shutdown_event (multiprocessing.Event): Event indicating shutdown
        _input_variables (Dict[str, Variable]): List of input variables
        _output_variables (Dict[str, Variable]): List of output variables
        _in_queue (multiprocessing.Queue): input variable queue
        _out_queue (multiprocessing.Queue): output variable update queue
        _providers (dict): Dictionary mapping pvname to p4p provider
        _running_indicator (multiprocessing.Value): Boolean indicator of running model execution
        _monitors (dict): Dictionary of monitor objects for read-only server
        _cached_values (dict): Dict for caching values while model executes
        _pvname_to_varname_map (dict): Mapping of pvname to variable name
        _varname_to_pvname_map (dict): Mapping of variable name to pvame

    """

    protocol = "pva"

    def __init__(
        self,
        input_variables: Dict[str, Variable],
        output_variables: Dict[str, Variable],
        epics_config: dict,
        in_queue: multiprocessing.Queue,
        out_queue: multiprocessing.Queue,
        running_indicator: Synchronized,
        *args,
        **kwargs,
    ) -> None:
        """Initialize server process.

        Args:
            input_variables (Dict[str, Variable]): Dictionary mapping pvname to lume-model input variable.

            output_variables (Dict[str, Variable]):Dictionary mapping pvname to lume-model output variable.

            epics_config (dict): Dictionary describing EPICS configuration for model variables

            in_queue (multiprocessing.Queue): Queue for tracking updates to input variables

            out_queue (multiprocessing.Queue): Queue for tracking updates to output variables

            running_indicator (Synchronized): Boolean indicator indicating running model execution

        """

        super().__init__(*args, **kwargs)
        self.pva_server = None
        self.exit_event = multiprocessing.Event()
        self.shutdown_event = multiprocessing.Event()
        self._input_variables = input_variables
        self._output_variables = output_variables
        self._epics_config = epics_config
        self._in_queue = in_queue
        self._out_queue = out_queue
        self._providers: Dict[str, SharedPV|None] = {}
        self._running_indicator = running_indicator
        # monitors for read only
        self._monitors = {}
        self._cached_values = {}
        self._field_to_parent_map = {}
        self._input_values = {}
        self._output_values = {}

        # utility maps
        self._pvname_to_varname_map = {
            config["pvname"]: var_name for var_name, config in epics_config.items()
        }
        self._varname_to_pvname_map = {
            var_name: config["pvname"] for var_name, config in epics_config.items()
        }

    def update_pv(self, pvname: str, value: Union[np.ndarray, float]) -> None:
        """Adds update to input process variable to the input queue.

        Args:
            pvname (str): Name of process variable

            value (Union[np.ndarray, float]): Value to set

        """
        # Hack for now to get the pickable value
        value = value.raw.value

        varname = self._pvname_to_varname_map[pvname]
        var = self._input_variables[varname]
        model_variable = type_handler(var).default_value(var)

        # check for already cached variable
        model_variable = self._cached_values.get(varname, model_variable)

        self._cached_values[varname] = model_variable
        self._input_values[varname] = value

        # only update if not running
        if not self._running_indicator.value:
            self._in_queue.put({"protocol": self.protocol, "vars": self._cached_values, "vals": self._input_values})
            self._cached_values = {}

    def _monitor_callback(self, pvname, V) -> None:
        """Callback function used for updating read_only process variables."""
        value = V.raw.value
        varname = self._pvname_to_varname_map[pvname]
        var = self._input_variables[varname]
        model_variable = type_handler(var).default_value(var)

        if not model_variable:
            model_variable = self._output_variables[varname]

        # check for already cached variable
        model_variable = self._cached_values.get(varname, model_variable)

        self._cached_values[varname] = model_variable
        self._input_values[varname] = value

        # only update if not running
        if not self._running_indicator.value:
            self._in_queue.put({"protocol": self.protocol, "vars": self._cached_values, "vals": self._input_values})
            self._cached_values = {}

    def _make_timestamp(self, ts: float) -> Tuple[int, int]:
        """
        Converts a timestamp into a tuple that can be fed to EPICS

        Parameters
        ----------
        ts : float
            Timestamp, in seconds since UNIX epoch

        Returns
        -------
        Tuple[int, int]
            (Seconds, nanoseconds) since epoch
        """
        f, i = math.modf(ts)
        return (i, int(f * 1e9))

    def _update_timestamp(self, pv: Value, ts: float = 0) -> None:
        """
        Updates the timestamp on a PV structure, if it has one

        Parameters
        ----------
        pv : Value
            PV to update
        ts : float
            Timestamp in seconds since UNIX epoch
        """
        if 'timeStamp' not in pv:
            return

        sec, nsec = self._make_timestamp(ts if ts > 0 else time.time())
        pv['timeStamp']['secondsPastEpoch'] = sec
        pv['timeStamp']['nanoseconds'] = nsec

    def _initialize_model(self):
        """Initialize model"""

        rep = {"protocol": "pva", "vars": self._input_variables, "vals": self._input_values}

        self._in_queue.put(rep)

    def _create_monitor(self, variable: Variable, config: dict) -> None:
        """
        Creates a new monitored remote PV

        Parameters
        ----------
        variable : Variable
            LUME variable
        config : dict
            Configuration
        """
        pvname = config.get("pvname")

        if variable.name in self._input_variables:
            self._monitors[pvname] = self._context.monitor(
                pvname, partial(self._monitor_callback, pvname)
            )
        # in this case, externally hosted output variable
        else:
            self._providers[pvname] = None

    def _create_summary(self):
        """Creates the summary PV, describing the model"""
        pvname = self._epics_config["summary"].get("pvname")
        owner = self._epics_config["summary"].get("owner")
        date_published = self._epics_config["summary"].get("date_published")
        description = self._epics_config["summary"].get("description")
        id = self._epics_config["summary"].get("id")

        spec = [
            ("id", "s"),
            ("owner", "s"),
            ("date_published", "s"),
            ("description", "s"),
            ("input_variables", "as"),
            ("output_variables", "as"),
        ]
        values = {
            "id": id,
            "date_published": date_published,
            "description": description,
            "owner": owner,
            "input_variables": [
                self._epics_config[var]["pvname"]
                for var in self._input_variables
            ],
            "output_variables": [
                self._epics_config[var]["pvname"]
                for var in self._input_variables
            ],
        }

        pv_type = Type(id="summary", spec=spec)
        value = Value(pv_type, values)
        pv = SharedPV(initial=value)
        self._providers[pvname] = pv

    def _create_struct(self, config: dict, variable_name: str, variables: Dict[str, Variable]) -> None:
        """
        Create a new structure

        Parameters
        ----------
        config : dict
            Configuration for this structure/variable, from the YAML file
        variable_name : str
            Name of the variable
        variables : Dict[str, Variable]
            List of variables described already
        """
        spec = []
        structure = {}

        fields = config.get("fields")
        pvname = config.get("pvname")

        for field in fields:
            # track fields in dict
            self._field_to_parent_map[field] = variable_name
            variable = variables[field]
            initial = variable.default_value

            if variable is None:
                raise ValueError(
                    f"Field {field} for {variable_name} not found in variable list"
                )

            handler = type_handler(variable)
            if handler is None:
                raise ValueError(f"Unsupported variable type provided: {type(variable)}")

            initial = handler.initial_value(config, variable)
            spec.append((field, 'v')) # Using variant here because we can't extract tuple struct desc from the NT types in p4p...

            structure[field] = initial

        # Set default output var value
        self._output_values[variable.name] = initial

        # Assemble type and value
        struct_type = Type(id=variable_name, spec=spec)
        struct_value = Value(struct_type, structure)

        # Store off type and current value
        self._structures[variable_name] = structure
        self._structure_types[variable_name] = struct_type
        pv = SharedPV(initial=struct_value)
        self._providers[pvname] = pv

    def _create_variable(self, config: dict, variable: Variable) -> None:
        """
        Create a new variable

        Parameters
        ----------
        config : dict
            Configuration for this variable
        variable : Variable
            LUME variable
        """
        pvname = config.get("pvname")

        handler = type_handler(variable)
        if handler is None:
            raise ValueError(f"Unsupported variable type provided: {type(variable)}")

        # Create an initial Value()
        initial = handler.initial_value(config, variable)

        if variable.name in self._input_variables:
            handler = PVAccessInputHandler(
                pvname=pvname,
                is_constant=variable.is_constant,
                server=self,
            )
            pv = SharedPV(handler=handler, initial=initial)
        else:
            pv = SharedPV(initial=initial)

        # Set default output var value
        self._output_values[variable.name] = initial
        self._providers[pvname] = pv

    def setup_server(self) -> None:
        """Configure and start server."""

        self._context = Context()

        # update value with stored defaults
        for var_name in self._input_variables:
            if self._epics_config[var_name]["serve"]:
                self._input_values[var_name] = self._input_variables[
                    var_name
                ].default_value

            else:
                if self._context is None:
                    self._context = Context("pva")

                try:
                    val = self._context.get(self._varname_to_pvname_map[var_name])
                    val = val.raw.value

                except:
                    self.exit_event.set()
                    raise ValueError(
                        f"Unable to connect to {self._varname_to_pvname_map[var_name]}"
                    )

                self._input_values[var_name] = val

        # update output variable values
        self._initialize_model()
        model_outputs = None
        while not self.shutdown_event.is_set() and model_outputs is None:
            try:
                model_outputs = self._out_queue.get(timeout=0.1)
            except Empty:
                pass

        # No need to do this if we're being shutdown
        if self.shutdown_event.is_set():
            return

        model_output_vars = model_outputs.get("output_variables", {})
        self._output_variables.update(model_output_vars)
        
        variables = copy.deepcopy(self._input_variables)
        variables.update(self._output_variables)
        
        # ignore interrupt in subprocess
        signal.signal(signal.SIGINT, signal.SIG_IGN)
        logger.info("Initializing pvAccess server")
        
        # initialize global inputs
        self._structures = {}
        self._structure_types: Dict[str, Type] = {}

        # Initialize all of the variables specified in our config
        for variable_name, config in self._epics_config.items():
            # Not served, create a monitor
            if not config["serve"]:
                self._create_monitor(variables[variable_name], config)
                continue

            # Handle structures
            if "fields" in config:
                self._create_struct(config, variable_name, variables)
            else:
                self._create_variable(config, variables[variable_name])

        # Create a summary PV, if requested.
        if "summary" in self._epics_config:
            self._create_summary()

        # initialize pva server
        self.pva_server = P4PServer(providers=[self._providers])

        logger.info("pvAccess server started")

    def update_pvs(
        self,
        input_variables: Dict[str, Variable],
        output_variables: Dict[str, Variable],
        output_values: Dict[str, Any]
    ) -> None:
        """Update process variables over pvAccess.

        Args:
            input_variables (Dict[str, Variable]): Dict of lume-epics output variables.

            output_variables (Dict[str, Variable]): Dict of lume-model output variables.

        """
        variables = input_variables
        variables.update(output_variables)

        for variable in variables.values():
            parent = self._field_to_parent_map.get(variable.name)

            if variable.name in self._input_variables and isinstance(variable, ScalarVariable) and variable.is_constant:
                logger.debug("Cannot update constant variable.")
                continue
            else:
                # do not build attribute pvs
                logger.debug(
                    "pvAccess process variable %s updated with value %s.",
                    variable.name,
                    output_values[variable.name],
                )
                value = output_values[variable.name]

            handler = type_handler(variable)

            # update structure or pv
            if parent:
                self._structures[parent][variable.name]['value'] = value
                value = Value(self._structure_types[parent], self._structures[parent])
                pvname = self._varname_to_pvname_map[parent]
                output_provider = self._providers[pvname]

                self._update_timestamp(value[variable.name])

            else:
                pvname = self._varname_to_pvname_map[variable.name]
                output_provider = self._providers[pvname]

            if output_provider:
                # Convert to value if it hasn't been already
                if not isinstance(value, Value):
                    value = handler.to_value(value)

                self._update_timestamp(value)
                output_provider.post(value)

            # in this case externally hosted
            else:
                try:
                    self._context.put(pvname, value)
                except:
                    self.exit_event.set()
                    self.shutdown()

    def run(self) -> None:
        """Start server process."""
        self.setup_server()

        # mark running
        while not self.shutdown_event.is_set():
            try:
                data = self._out_queue.get_nowait()
                inputs = data.get("input_variables", {})
                outputs = data.get("output_variables", {})
                output_values = data.get("output_values", {})
                self.update_pvs(inputs, outputs, output_values)

                # check cached values
                if len(self._cached_values) > 0 and not self._running_indicator.value:
                    self._in_queue.put(
                        {"protocol": self.protocol, "vars": self._cached_values, "vals": self._input_values}
                    )

            except Empty:
                time.sleep(0.1)
                logger.debug("out queue empty")

        self._context.close()
        if self.pva_server is not None:
            self.pva_server.stop()

        logger.info("pvAccess server stopped.")

    def shutdown(self):
        """Safely shutdown the server process."""
        self.shutdown_event.set()


class PVAccessInputHandler:
    """
    Handler object that defines the callbacks to execute on put operations to input
    process variables.
    This will proxy PUT operations into the internal cache.
    """

    def __init__(self, pvname: str, is_constant: bool, server: PVAServer):
        """
        Initialize the handler with prefix and image pv attributes

        Args:
            pvname (str): The PV being handled
            is_constant (bool): Indicator of constant variable
            server (PVAServer): Reference to the server holding this PV

        """
        self.is_constant = is_constant
        self.pvname = pvname
        self.server = server

    def put(self, pv: SharedPV, op: ServOpWrap) -> None:
        """Updates the global input process variable state, posts the input process
        variable value change, runs the thread local BaseModel instance
        using the updated global input process variable states, and posts the model
        output values to the output process variables.

        Args:
            pv (SharedPV): Input process variable on which the put operates.

            op (ServOpWrap): Server operation initiated by the put call.

        """
        # update input values and global input process variable state
        if not self.is_constant and op.value() is not None:
            pv.post(op.value())
            self.server.update_pv(pvname=self.pvname, value=op.value())
        # mark server operation as complete
        op.done()
