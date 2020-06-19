import copy
import numpy as np
import random
from typing import Dict, Mapping, Union, List

from epics import caget
from pcaspy import Driver, SimpleServer

from lume_epics.model import OnlineSurrogateModel
from lume_epics import IMAGE_VARIABLE_TYPES, SCALAR_VARIABLE_TYPES
from lume_epics.epics_server.ca import build_pvdb, SimDriver
from lume_epics.epics_server.pva import ModelLoader, InputHandler


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
        model_class,
        model_kwargs: dict,
        input_variables,
        output_variables,
        prefix: str,
    ) -> None:
        """
        Create OnlineSurrogateModel instance and initialize output variables by running \\
        with the input process variable state, set up the proces variable database and \\
        input/output variable tracking, start the server, create the process variables, \\
        and start the driver.

        Parameters
        ----------
        model_class
            Model class to be instantiated

        model_kwargs: dict
            kwargs for initialization

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
        input_pvs = {}

        surrogate_model = model_class(**model_kwargs)
        self.model = OnlineSurrogateModel(
            [surrogate_model], input_variables, output_variables
        )

        # set up db for initializing process variables
        variable_dict = {**input_variables, **output_variables}
        self.pvdb = build_pvdb(variable_dict)

        # get starting output from the model and set up output process variables
        output_variables = self.model.run(input_variables)

        # initialize channel access server
        self.server = SimpleServer()

        # create all process variables using the process variables stored in self.pvdb
        # with the given prefix
        self.server.createPV(prefix + ":", self.pvdb)

        # set up driver for handing read and write requests to process variables
        self.driver = SimDriver(input_variables, output_variables)

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
        Start the channel access server and continually update.
        """
        sim_pv_state = copy.deepcopy(self.input_pv_state)

        # Initialize output variables
        print("Initializing sim...")
        output_pv_state = self.model.run(self.input_pv_state)
        self.driver.set_output_pvs(output_pv_state)
        print("...finished initializing.")

        self.server = Server.forever(providers=[providers])

        try:
            while True:
                # process channel access transactions
                self.server.process(0.1)

                # check if the input process variable state has been updated as
                # an indicator of new input values
                while not all(
                    np.array_equal(sim_pv_state[key], self.input_pv_state[key])
                    for key in self.input_pv_state
                ):

                    sim_pv_state = copy.deepcopy(self.input_pv_state)
                    model_output = self.model.run(self.input_pv_state)
                    self.driver.set_output_pvs(model_output)

        except KeyboardInterrupt:
            print("Terminating server.")

    def stop_server(self) -> None:
        """
        Stop the channel access server.
        """
        self.server.stop()
