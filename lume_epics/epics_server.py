import copy
import numpy as np
import random
import sys
import time
import threading
from typing import Dict, Mapping, Union, List

from epics import caget
from pcaspy import Driver, SimpleServer

from p4p.nt import NTScalar, NTNDArray
from p4p.server.thread import SharedPV
from p4p.server import Server as P4PServer
from p4p.nt.ndarray import ntndarray as NTNDArrayData


from lume_epics.model import OnlineSurrogateModel
from lume_epics import IMAGE_VARIABLE_TYPES, SCALAR_VARIABLE_TYPES
from lume_epics.epics_server.ca import build_pvdb, SimDriver


def build_pvdb(variables):
    pvdb = {}

    for variable in variables.values():
        if isinstance(variable, IMAGE_VARIABLE_TYPES):

            # infer color mode
            if variable.value.ndim == 2:
                color_mode == 0

            else:
                raise Exception("Color mode cannot be inferred from image shape.")

            image_pvs = build_image_pvs(
                variable.name,
                variable.shape,
                variable.units,
                variable.precision,
                variable.color_mode,
            )

            # assign default PVS
            pvdb = {
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
                f"{pvname}:ArraySizeX_RBV": {
                    "type": "int",
                    "value": variable.value.shape[0],
                },
                f"{pvname}:ArraySizeY_RBV": {
                    "type": "int",
                    "value": variable.value.shape[1],
                },
                f"{pvname}:ArraySize_RBV": {
                    "type": "int",
                    "value": int(np.prod(variable.value.shape)),
                },
                f"{pvname}:ArrayData_RBV": {
                    "type": "float",
                    "prec": variable.precision,
                    "count": int(np.prod(variable.value.shape)),
                    "units": variable.units,
                },
                f"{pvname}:MinX_RBV": {"type": "float", "value": variable.x_min},
                f"{pvname}:MinY_RBV": {"type": "float", "value": variable.y_min},
                f"{pvname}:MaxX_RBV": {"type": "float", "value": variable.x_max},
                f"{pvname}:MaxY_RBV": {"type": "float", "value": variable.y_max},
                f"{pvname}:ColorMode_RBV": {"type": "int", "value": color_mode},
            }

            # placeholder for color images, not yet implemented
            if ndim > 2:
                pvdb[f"{pvname}:ArraySizeZ_RBV"] = {
                    "type": "int",
                    "value": variable.value.shape[2],
                }

        else:
            pvdb[variable.name] = variable.dict(exclude_unset=True, exclude={"io_type"})

    return pvdb


class SimDriver(Driver):
    """
    Class that reacts to read an write requests to process variables.

    Attributes
    ----------
    input_pv_state: dict
        Dictionary mapping initial input process variables to values.

    output_pv_state: dict
        Dictionary mapping initial output process variables to values (np.ndarray in \\
        the case of image x:y)

    """

    def __init__(self, input_variables, output_variables) -> None:
        """
        Initialize the driver. Store input state and output state.

        Parameters
        ----------
        input_pv_state: dict
            Dictionary that maps the input process variables to their inital values

        output_pv_state:
            Dictionary that maps the output process variables to their inital values

        """

        super(SimDriver, self).__init__()

        # track input state and output state
        self.input_variables = input_variables
        self.output_variables = output_variables

    def read(self, pvname: str) -> Union[float, np.ndarray]:
        """
        Method used by server when clients read a process variable.

        Parameters
        ----------
        pv: str
            Process variable name

        Returns
        -------
        float/np.ndarray
            Returns the value of the process variable

        Notes
        -----
        In the pcaspy documentation, 'reason' is used instead of pv.

        """
        return self.getParam(pvname)

    def write(self, pv: str, value: Union[float, np.ndarray]) -> bool:
        """
        Method used by server when clients write a process variable.


        Parameters
        ----------
        pv: str
            Process variable name

        value: float/np.ndarray
            Value to assign to the process variable.

        Returns
        -------
        bool
            Returns True if the value is accepted, False if rejected

        Notes
        -----
        In the pcaspy documentation, 'reason' is used instead of pv.
        """

        if pv in self.output_variables:
            print(pv + " is a read-only pv")
            return False

        else:

            if pv in self.input_variables:
                self.input_pv_state[pv] = value

            self.setParam(pv, value)
            self.updatePVs()

            return True

    def set_output_pvs(self, output_variables) -> None:
        """
        Set output process variables.

        Parameters
        ----------
        output_pvs: dict
            Dictionary that maps ouput process variable name to variables
        """

        for variable_name, variable in output_variables.items():
            if isinstance(variable, IMAGE_VARIABLE_TYPES):
                value = variable.value.flatten()

                self.setParam(
                    variable_name + ":ArrayData_RBV", variable.value.flatten()
                )
                self.setParam(variable_name + ":MinX_RBV", variable.min_x)
                self.setParam(variable_name + ":MinY_RBV", variable.min_y)
                self.setParam(variable_name + ":MaxX_RBV", variable.max_x)
                self.setParam(variable_name + ":MaxY_RBV", variable.max_y)
                self.output_variables[variable_name].value = variable.value.flatten()

            else:
                self.setParam(variable_name, variable.value)
                self.output_variables[variable_name].value = variable.value


class ModelLoader(threading.local):
    """
    Subclass of threading.local that will initialize the surrogate model in each \\
    thread.

    Attributes
    ----------
    model: 
        Surrogate model instance used for predicting

    Note
    ----
    Keras models are not thread safe so the model must be loaded in each thread and \\
    referenced locally.
    """

    def __init__(
        self, model_class, model_kwargs: dict, input_variables, output_variables
    ) -> None:
        """
        Initializes surrogate model.

        Parameters
        ----------
        model_class
            Model class to be instantiated

        model_kwargs: dict
            kwargs for initialization
        """

        surrogate_model = model_class(**model_kwargs)
        self.model = OnlineSurrogateModel(
            [surrogate_model], input_variables, output_variables
        )


class InputHandler:
    """
    Handler object that defines the callbacks to execute on put operations to input \\
    process variables.
    """

    def __init__(self, prefix: str):
        """
        Initialize the handler with prefix and image pv attributes

        prefix: str
            prefix used to format pvs

        image_pvs: list
            List of image process variables to format

        """
        self.prefix = prefix

    def put(self, pv, op) -> None:
        """
        Updates the global input process variable state, posts the input process \\
        variable value change, runs the thread local OnlineSurrogateModel instance \\
        using the updated global input process variable states, and posts the model \\
        output values to the output process variables.

        Parameters
        ----------
        pv: p4p.server.thread.SharedPV
            Input process variable on which the put is operating

        op: p4p.server.raw.ServOpWrap
            Server operation initiated by the put call

        """
        global providers
        global input_pvs

        # update input values and global input process variable state
        pv.post(op.value())
        input_pvs[op.name().replace(f"{self.prefix}:", "")].value = op.value()

        # run model using global input process variable state
        output_variables = model_loader.model.run(input_pvs)

        for variable in output_variables.values():
            if isinstance(variable, IMAGE_VARIABLE_TYPES):

                nd_array = variable.value.flatten()
                # get dw and dh from model output
                nd_array.attrib = {
                    "min_x": variable.min_x,
                    "min_y": variable.min_y,
                    "max_x": variable.max_x,
                    "max_y": variable.max_y,
                }

                output_provider = providers[
                    f"{self.prefix}:{variable.name}:ArrayData_RBV"
                ]
                output_provider.post(nd_array)

            # do not build attribute pvs
            else:
                output_provider = providers[f"{self.prefix}:{variable.name}"]
                output_provider.post(variable.value)

        # mark server operation as complete
        op.done()


class Server:
    """
    Server object for channel access process variables that updates and reads process \\
    values in a single thread.

    Attributes
    ----------
    model: online_model.model.surrogate_model.OnlineSurrogateModel
        OnlineSurrogateModel instance used for getting predictions

    input_variables: 
        Dictionary that maps the input process variables to their current values

    ouput_variables:
        Dictionary that maps the output process variables to their current values

    server: pcaspy.driver.SimpleServer
        Server class that interfaces between the channel access client and the driver. \\
        Forwards the read/write requests to the driver

    driver: online_model.server.ca.SimDriver
        Class that reacts to process variable read/write requests

    """

    def __init__(
        self,
        model_class: ,
        model_kwargs: dict,
        input_variables,
        output_variables,
        prefix: str,
        protocol: List[str] = ["ca", "pva"],
    ) -> None:
        """
        Create OnlineSurrogateModel instance in the main thread and initialize output \\
        variables by running with the input process variable state, input/output variable \\
        tracking, start the server, create the process variables, \\
        and start the driver.

        Parameters
        ----------
        model_class
            Model class to be instantiated

        model_kwargs: dict
            kwargs for initialization

        input_variables:

        output_variables:

        prefix: str
            Prefix used to format process variables

        array_pvs: list
            List of image pvs that need to be served


        """

        # need these to be global to access from threads
        global providers
        global input_pvs
        global model_loader

        providers = {}
        input_pvs = input_variables
        self.input_variables = input_variables
        self.output_variables = output_variables
        self.prefix = prefix
        self.protocol = protocol

        # initialize loader for model
        model_loader = ModelLoader(
            model_class, model_kwargs, input_variables, output_variables
        )

        # get starting output from the model and set up output process variables
        self.output_variables = model_loader.model.run(input_variables)

        # initialize server based on protocols passed
        if "ca" in self.protocol:
            self.initialize_ca_server()

        if "pva" in self.protocol:
            self.initialize_pva_server()

    def initialize_ca_server(self) -> None:
        # set up db for initializing process variables
        variable_dict = {**self.input_variables, **self.output_variables}
        self.pvdb = build_pvdb(variable_dict)

        # initialize channel access server
        self.ca_server = SimpleServer()

        # create all process variables using the process variables stored in self.pvdb
        # with the given prefix
        self.ca_server.createPV(self.prefix + ":", self.pvdb)

        # set up driver for handing read and write requests to process variables
        self.driver = SimDriver(self.input_variables, self.output_variables)
        self.driver.set_output_pvs(self.output_variables)

    def initialize_pva_server(self) -> None:
        # initialize global inputs
        for variable_name, variable in self.input_variables.items():
            # input_pvs[variable.name] = variable.value
            pvname = f"{self.prefix}:{variable_name}"

            # prepare scalar variable types
            if isinstance(variable, SCALAR_VARIABLE_TYPES):
                pv = SharedPV(
                    handler=InputHandler(
                        self.prefix
                    ),  # Use InputHandler class to handle callbacks
                    nt=NTScalar("d"),
                    initial=variable.value,
                )
            elif isinstance(variable, IMAGE_VARIABLE_TYPES):
                pv = SharedPV(
                    handler=InputHandler(
                        self.prefix
                    ),  # Use InputHandler class to handle callbacks
                    nt=NTNDArray(),
                    initial=variable.value,
                )

            providers[pvname] = pv

        # use default handler for the output process variables
        # updates to output pvs are handled from post calls within the input update
        for variable_name, variable in self.output_variables.items():
            pvname = f"{self.prefix}:{variable_name}"
            if isinstance(variable, SCALAR_VARIABLE_TYPES):
                pv = SharedPV(nt=NTScalar(), initial=variable.value)

            elif isinstance(variable, IMAGE_VARIABLE_TYPES):
                pv = SharedPV(nt=NTNDArray(), initial=variable.value)

            providers[pvname] = pv

        else:
            pass  # throw exception for incorrect data type

    def start_ca_server(self) -> None:
        sim_state = {
            variable.name: variable.value for variable in self.input_variables.values()
        }

        try:
            while True:
                # process channel access transactions
                self.ca_server.process(0.1)

                # check if the input process variable state has been updated as
                # an indicator of new input values
                while not all(
                    np.array_equal(sim_state[key], self.input_variables[key].value)
                    for key in self.input_variables
                ):
                    sim_state = {
                        variable.name: variable.value
                        for variable in self.input_variables.values()
                    }
                    model_output = self.model.run(self.input_variables)
                    self.driver.set_output_pvs(model_output)


    def start_pva_server(self) -> None:
        self.pva_server = P4PServer(providers=[providers])

    def start_server(self) -> None:
        """
        Starts a server

        """

        if "ca" in self.protocol:
            ca_thread = threading.Thread(target=self.start_ca_server, daemon=True)
            ca_thread.start()

        if "pva" in self.protocol:
            self.start_pva_server()

        try:
            while True:
                time.sleep(2)

        except KeyboardInterrupt:
            # Ctrl-C handling and send kill to threads
            print("Stopping servers...")
            if "pva" in self.protocol:
                self.pva_server.stop()

            sys.exit()

    def stop_server(self) -> None:
        """
        Stop the channel access server.
        """
        if "ca" in self.protocol:
            self.ca_server.stop()

        if "pva" in self.protocol:
            self.pva_server.stop()
