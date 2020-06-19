import threading
import numpy as np
from typing import Dict, List, Union

from p4p.nt import NTScalar, NTNDArray
from p4p.server.thread import SharedPV
from p4p.server import Server
from p4p.nt.ndarray import ntndarray as NTNDArrayData

from lume_model.variables import Variable

from lume_epics import (
    SCALAR_VARIABLE_TYPES,
    IMAGE_VARIABLE_TYPES,
    INPUT_VARIABLE_TYPES,
    OUTPUT_VARIABLE_TYPES,
)
from lume_epics.model import OnlineSurrogateModel




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
        input_pvs[op.name().replace(f"{self.prefix}:", "")] = op.value()

        # run model using global input process variable state
        output_variables = model_loader.model.run(input_pvs)

        for variable_name, variable in output_variables:
            if isinstance(variable, IMAGE_VARIABLE_TYPES):
                rebuilt_output[f"{variable_name}:ArrayData_RBV"] = 
                
                nd_array = variable.value.flatten()
                # get dw and dh from model output
                nd_array.attrib = {
                    "min_x": variable.min_x,
                    "min_y": variable.min_y,
                    "max_x": variable.max_x,
                    "max_y": variable.max_y,
                }

                output_provider = providers[f"{variable_name}:ArrayData_RBV"]
                output_provider.post(nd_array)

            # do not build attribute pvs
            else:
                rebuilt_output[variable_name] = variable.value
                output_provider = providers[f"{self.prefix}:{variable_name}"]
                output_provider.post(variable.value)


        # mark server operation as complete
        op.done()


class PVAServer:
    """
    Server object for PVA process variables.

    Attributes
    ----------

    """

    def __init__(
        self,
        model_class,
        model_kwargs: dict,
        input_variables: List[Variable],
        output_variables: List[Variable],
        prefix: str,
    ) -> None:
        """
        Initialize the global process variable list, populate the initial values for \\
        the global input variable state, generate starting output from the main thread \\
        OnlineSurrogateModel model instance, and initialize input and output process \\
        variables.

        Parameters
        ----------
        model_class: class
            Model class to be instantiated

        model_kwargs: dict
            kwargs for initialization

        variables: list
            List of lume_model.variables.Variable objects

        prefix: str
            Prefix to use when serving
        """
        # need these to be global to access from threads
        global providers
        global input_pvs
        global model_loader

        providers = {}
        input_pvs = {}

        # initialize loader for model
        model_loader = ModelLoader(
            model_class, model_kwargs, input_variables, output_variables
        )

        # initialize global inputs
        for variable_name, variable in input_variables.items():
            input_pvs[variable.name] = variable.value

            # prepare scalar variable types
            if isinstance(variable, SCALAR_VARIABLE_TYPES):
                pvname = f"{prefix}:{variable_name}"

                pv = SharedPV(
                    handler=InputHandler(
                        prefix
                    ),  # Use InputHandler class to handle callbacks
                    nt=NTScalar("d"),
                    initial=variable.value,
                )
            elif isinstance(variable, IMAGE_VARIABLE_TYPES):
                pv = SharedPV(
                    handler=InputHandler(
                        prefix
                    ),  # Use InputHandler class to handle callbacks
                    nt=NTNDArray(),
                    initial=variable.value,
                )
            providers[variable_name] = pv

        # use main thread loaded model to do initial model run
        starting_output = model_loader.model.run(input_pvs)
        for var in output_variables:
            var.value = starting_output[var.name]

        # use default handler for the output process variables
        # updates to output pvs are handled from post calls within the input update
        for variable_name, variable in output_variables.items():
            pvname = f"{prefix}:{variable_name}"
            if isinstance(variable, SCALAR_VARIABLE_TYPES):
                pv = SharedPV(nt=NTScalar(), initial=variable.value)

            elif isinstance(variable, IMAGE_VARIABLE_TYPES):
                pv = SharedPV(nt=NTNDArray(), initial=variable.value)

            providers[variable_name] = pv

        else:
            pass  # throw exception for incorrect data type

    def start_server(self) -> None:
        """
        Starts the server and runs until KeyboardInterrupt.
        """
        print("Starting Server...")
        self.server = Server.forever(providers=[providers])

    def stop_server(self) -> None:
        """
        Stops the server manually.
        """
        print("Stopping Server...")
        self.server.stop()
