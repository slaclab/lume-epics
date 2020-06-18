import copy
import numpy as np
import random
from typing import Dict, Mapping, Union, List

from epics import caget
from pcaspy import Driver, SimpleServer

from lume_epics.model import OnlineSurrogateModel
from lume_epics import IMAGE_VARIABLE_TYPES, SCALAR_VARIABLE_TYPES


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
                f"{pvname}:ColorMode_RBV": {"type": "int", "value": color_mode},
                f"{pvname}:dw": {"type": "float", "prec": variable.precision},
                f"{pvname}:dh": {"type": "float", "prec": variable.precision},
                f"{pvname}:ArraySizeY_RBV": {
                    "type": "int",
                    "value": variable.value.shape[1],
                },
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


def format_model_output(model_output):
    """
    Reformat model for ca server compatibility.

    Parameters
    ----------
    model_ouptut: dict
        Output from the surrogate model.

    Returns
    -------
    dict
        Output with appropriate data label.
    """
    rebuilt_output = {}
    for variable_name, variable in model_output.items():
        if isinstance(variable, IMAGE_VARIABLE_TYPES):
            rebuilt_output[f"{variable_name}:ArrayData_RBV"] = variable.value.flatten()
        else:
            rebuilt_output[variable_name] = variable.value

    return rebuilt_output


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

    def __init__(
        self,
        input_pv_state: Dict[str, float],
        output_pv_state: Mapping[str, Union[float, np.ndarray]],
    ) -> None:
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
        self.input_pv_state = input_pv_state
        self.output_pv_state = output_pv_state

    def read(self, pv: str) -> Union[float, np.ndarray]:
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
        if pv in self.output_pv_state:
            value = self.getParam(pv)
        else:
            value = self.getParam(pv)

        return value

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

        if pv in self.output_pv_state:
            print(pv + " is a read-only pv")
            return False

        else:

            if pv in self.input_pv_state:
                self.input_pv_state[pv] = value

            self.setParam(pv, value)
            self.updatePVs()

            return True

    def set_output_pvs(
        self, output_pvs: Mapping[str, Union[float, np.ndarray]]
    ) -> None:
        """
        Set output process variables.

        Parameters
        ----------
        output_pvs: dict
            Dictionary that maps ouput process variable name to values
        """
        # update output process variable state
        self.output_pv_state.update(output_pvs)

        # update the output process variables that have been changed
        for pv in output_pvs:
            value = self.output_pv_state[pv]

            # set parameter with value
            self.setParam(pv, value)


class CAServer:
    """
    Server object for channel access process variables that updates and reads process \\
    values in a single thread.

    Attributes
    ----------
    model: online_model.model.surrogate_model.OnlineSurrogateModel
        OnlineSurrogateModel instance used for getting predictions

    pvdb: dict
        Dictionary that maps the process variable string to type (str), prec \\
        (precision), value (float), units (str), range (List[float])

    input_pv_state: dict
        Dictionary that maps the input process variables to their current values

    output_pv_state:
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

        in_pvdb: dict
            Dictionary that maps the input process variable string to type (str), prec \\
             (precision), value (float), units (str), range (List[float])

        out_pvdb: dict
            Dictionary that maps the output process variable string to type (str), prec \\
            (precision), value (float), units (str), range (List[float])

        prefix: str
            Prefix used to format process variables

        array_pvs: list
            List of image pvs that need to be served


        """
        surrogate_model = model_class(**model_kwargs)
        self.model = OnlineSurrogateModel(
            [surrogate_model], input_variables, output_variables
        )

        # output_pvdb = build_pvdb(output_variables)

        # set up db for initializing process variables

        variable_dict = {**input_variables, **output_variables}
        self.pvdb = build_pvdb(variable_dict)

        # set up input process variables
        self.input_pv_state = {
            variable.name: variable.value for variable in input_variables.values()
        }

        # get starting output from the model and set up output process variables
        self.output_pv_state = self.model.run(self.input_pv_state)
        self.output_pv_state = format_model_output(self.output_pv_state)

        # initialize channel access server
        self.server = SimpleServer()

        # create all process variables using the process variables stored in self.pvdb
        # with the given prefix
        self.server.createPV(prefix + ":", self.pvdb)

        # set up driver for handing read and write requests to process variables
        self.driver = SimDriver(self.input_pv_state, self.output_pv_state)

    def start_server(self) -> None:
        """
        Start the channel access server and continually update.
        """
        sim_pv_state = copy.deepcopy(self.input_pv_state)

        # Initialize output variables
        print("Initializing sim...")
        output_pv_state = self.model.run(self.input_pv_state)
        output_pv_state = format_model_output(output_pv_state)
        self.driver.set_output_pvs(output_pv_state)
        print("...finished initializing.")

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
                    model_output = format_model_output(model_output)
                    self.driver.set_output_pvs(model_output)

        except KeyboardInterrupt:
            print("Terminating server.")

    def stop_server(self) -> None:
        """
        Stop the channel access server.
        """
        self.server.stop()
