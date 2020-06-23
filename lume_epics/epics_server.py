import copy
import numpy as np
import random
import sys
import time
from threading import Thread, Event, local
from typing import Dict, Mapping, Union, List

from epics import caget
from pcaspy import Driver, SimpleServer

from p4p.nt import NTScalar, NTNDArray
from p4p.server.thread import SharedPV
from p4p.server import Server as P4PServer
from p4p.nt.ndarray import ntndarray as NTNDArrayData

from lume_model.variables import Variable
from lume_epics.model import OnlineSurrogateModel, SurrogateModel


def build_pvdb(variables: List[Variable]):
    """
    Utility function for building dictionary (pvdb) used to initialize 
    the channel access server.
    
    Parameters
    ----------
    variables: list
        List of lume_model variables to be served with channel access server.

    Returns
    -------
    pvdb: dict

    """
    pvdb = {}

    for variable in variables:
        if variable.variable_type == "image":

            # infer color mode
            if variable.value.ndim == 2:
                color_mode = 0

            else:
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
                pvdb[f"{variable.name}:ArrayData_RBV"]["units"] = variable.units

            # placeholder for color images, not yet implemented
            if variable.value.ndim > 2:
                pvdb[f"{variable.name}:ArraySizeZ_RBV"] = {
                    "type": "int",
                    "value": variable.value.shape[2],
                }

        else:
            pvdb[variable.name] = variable.dict(exclude_unset=True, exclude={"io_type"})

    return pvdb


class CADriver(Driver):
    """
    Class that reacts to read an write requests to process variables.

    Attributes
    ----------
    input_variables: list
        List of lume-model variables to use as inputs

    ouput_variables: list
        List of lume-model variables to use as outputs

    """

    def __init__(
        self, input_variables: List[Variable], output_variables: List[Variable],
    ) -> None:
        """
        Initialize the driver. Store input state and output state.

        Parameters
        ----------
        input_variables: list
            List of lume-model variables to use as inputs

        ouput_variables: list
            List of lume-model variables to use as outputs

        """

        super(CADriver, self).__init__()

        # track input state and output state
        self.input_variables = {variable.name: variable for variable in input_variables}
        self.output_variables = {
            variable.name: variable for variable in output_variables
        }

    def read(self, pvname: str) -> Union[float, np.ndarray]:
        """
        Method used by server when clients read a process variable.

        Parameters
        ----------
        pvnamme: str
            Process variable name

        Returns
        -------
        float/np.ndarray
            Returns the value of the process variable

        Notes
        -----
        In the pcaspy documentation, 'reason' is used instead of pvname.

        """
        return self.getParam(pvname)

    def write(self, pvname: str, value: Union[float, np.ndarray]) -> bool:
        """
        Method used by server when clients write a process variable.


        Parameters
        ----------
        pvname: str
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

        if pvname in self.output_variables:
            print(pvname + " is a read-only pv")
            return False

        else:
            if pvname in self.input_variables:
                self.input_variables[pvname].value = value
                self.setParam(pvname, value)
                self.updatePVs()
                return True

            else:
                print(f"{pvname} not found in server variables.")
                return False

    def set_output_pvs(self, output_variables: List[Variable]) -> None:
        """
        Set output process variables.

        Parameters
        ----------
        output_variables: list
            Dictionary that maps ouput process variable name to variables
        """

        for variable in output_variables:
            if variable.variable_type == "image":
                value = variable.value.flatten()

                self.setParam(
                    variable.name + ":ArrayData_RBV", variable.value.flatten()
                )
                self.setParam(variable.name + ":MinX_RBV", variable.x_min)
                self.setParam(variable.name + ":MinY_RBV", variable.y_min)
                self.setParam(variable.name + ":MaxX_RBV", variable.x_max)
                self.setParam(variable.name + ":MaxY_RBV", variable.y_max)
                self.output_variables[variable.name].value = variable.value.flatten()

            else:
                self.setParam(variable.name, variable.value)
                self.output_variables[variable.name].value = variable.value


class ModelLoader(local):
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
        self,
        model_class: SurrogateModel,
        model_kwargs: dict,
        input_variables,
        output_variables,
    ) -> None:
        """
        Initializes surrogate model.

        Parameters
        ----------
        model_class
            Model class to be instantiated. Should have all methods indicated by the abstract\\
            base class in 

        model_kwargs: dict
            kwargs for initialization
        """

        surrogate_model = model_class(**model_kwargs)
        self.model = OnlineSurrogateModel(
            [surrogate_model], input_variables, output_variables
        )


class PVAccessInputHandler:
    """
    Handler object that defines the callbacks to execute on put operations to input \\
    process variables.
    """

    def __init__(self, prefix: str):
        """
        Initialize the handler with prefix and image pv attributes

        prefix: str
            prefix used to format pvs

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

        for variable in output_variables:
            if variable.variable_type == "image":

                nd_array = variable.value.flatten()
                # get dw and dh from model output
                nd_array.attrib = {
                    "x_min": variable.x_min,
                    "y_min": variable.y_min,
                    "x_max": variable.x_max,
                    "y_max": variable.y_max,
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
        List of lume-model variables to use as inputs

    ouput_variables:
        List of lume-model variables to use as outputs

    server: pcaspy.driver.SimpleServer
        Server class that interfaces between the channel access client and the driver. \\
        Forwards the read/write requests to the driver

    driver: online_model.server.ca.CADriver
        Class that reacts to process variable read/write requests

    """

    def __init__(
        self,
        model_class: SurrogateModel,
        model_kwargs: dict,
        prefix: str,
        protocols: List[str] = ["ca", "pva"],
    ) -> None:
        """
        Create OnlineSurrogateModel instance in the main thread and initialize output \\
        variables by running with the input process variable state, input/output variable \\
        tracking, start the server, create the process variables, \\
        and start the driver.

        Parameters
        ----------
        model_class: lume_epics.model.SurrogateModel
            Surrogate model class to be instantiated

        model_kwargs: dict
            kwargs for initialization surrogate model

        prefix: str
            Prefix used to format process variables

        protocols: list
            List of protocols used to instantiate server


        """
        # check protocol conditions
        if not protocols:
            raise ValueError("Protocol must be provided to start server.")

        if any([protocol not in ["ca", "pva"] for protocol in protocols]):
            raise ValueError(
                'Invalid protocol provided. Protocol options are "pva" (PVAccess) and "ca" (Channel Access).'
            )

        # need these to be global to access from threads
        global providers
        global input_pvs
        global model_loader
        self.prefix = prefix
        self.protocols = protocols

        providers = {}

        self.input_variables = list(model_class.input_variables.values())
        self.output_variables = list(model_class.output_variables.values())

        # initialize loader for model
        model_loader = ModelLoader(
            model_class, model_kwargs, self.input_variables, self.output_variables
        )

        # get starting output from the model and set up output process variables
        self.output_variables = model_loader.model.run(self.input_variables)

        # initialize server based on protocols passed
        if "ca" in self.protocols:
            self.initialize_ca_server()

        if "pva" in self.protocols:
            self.initialize_pva_server()

    def initialize_ca_server(self) -> None:
        """
        Set up the channel access server.

        """
        # set up db for initializing process variables
        variable_dict = {
            variable.name: variable.value
            for variable in self.input_variables + self.output_variables
        }
        self.pvdb = build_pvdb(self.input_variables + self.output_variables)

        # initialize channel access server
        self.ca_server = SimpleServer()

        # create all process variables using the process variables stored in self.pvdb
        # with the given prefix
        self.ca_server.createPV(self.prefix + ":", self.pvdb)

        # set up driver for handing read and write requests to process variables
        self.driver = CADriver(self.input_variables, self.output_variables)
        self.driver.set_output_pvs(self.output_variables)

    def initialize_pva_server(self) -> None:
        """
        Set up pvaccess process variables for serving and start pvaccess server.

        """
        # initialize global inputs
        for variable in self.input_variables:
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
                )

            elif variable.variable_type == "image":
                pv = SharedPV(
                    handler=PVAccessInputHandler(
                        self.prefix
                    ),  # Use PVAccessInputHandler class to handle callbacks
                    nt=NTNDArray(),
                    initial=variable.value,
                )

            else:
                raise ValueError(
                    "Unsupported variable type provided: %s", variable.variable_type
                )

            providers[pvname] = pv

        # use default handler for the output process variables
        # updates to output pvs are handled from post calls within the input update
        for variable in self.output_variables:
            pvname = f"{self.prefix}:{variable.name}"
            if variable.variable_type == "scalar":
                pv = SharedPV(nt=NTScalar(), initial=variable.value)

            elif variable.variable_type == "image":
                pv = SharedPV(nt=NTNDArray(), initial=variable.value)

            else:
                raise ValueError(
                    "Unsupported variable type provided: %s", variable.variable_type
                )

            providers[pvname] = pv

        else:
            pass  # throw exception for incorrect data type

    def ca_thread(self, exit_event) -> None:
        """
        Thread used for the channel access server.

        Note
        ----
        To be used in a daemon thread.
        """

        sim_state = {variable.name: variable.value for variable in self.input_variables}

        while not exit_event.is_set():
            # process channel access transactions
            self.ca_server.process(0.1)

            # check if any input variable state has been updated
            # if so, run model and update output variables
            while not all(
                np.array_equal(sim_state[variable.name], variable.value)
                for variable in self.input_variables
            ):
                sim_state = {
                    variable.name: variable.value for variable in self.input_variables
                }
                model_output = self.model.run(self.input_variables)
                self.driver.set_output_pvs(model_output)

        print("Terminating Channel Access server.")

    def start_ca_server(self) -> None:
        """
        Start a Channel Access server.
        """
        self.exit_event = Event()

        self.ca_thread = Thread(
            target=self.ca_thread, daemon=True, args=(self.exit_event,)
        )
        self.ca_thread.start()

    def start_pva_server(self) -> None:
        """
        Start PVAccess server. 
        """
        self.pva_server = P4PServer(providers=[providers])

    def start(self) -> None:
        """
        Starts server depending on the passed server protocol.

        """

        # set up exit event for threads
        self.exit_event = Event()

        if "ca" in self.protocols:
            self.start_ca_server()

        if "pva" in self.protocols:
            self.start_pva_server()

        while not self.exit_event.is_set():
            try:
                time.sleep(0.1)

            except KeyboardInterrupt:
                # Ctrl-C handling and send kill to threads
                print("Stopping servers...")
                self.exit_event.set()
                if "pva" in self.protocols:
                    self.pva_server.stop()

                sys.exit()

    def stop(self) -> None:
        """
        Stop the channel access server.
        """
        if "ca" in self.protocols:
            self.exit_event.set()

        if "pva" in self.protocols:
            self.pva_server.stop()
