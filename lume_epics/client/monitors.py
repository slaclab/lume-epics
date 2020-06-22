import time

import numpy as np
from typing import List, Dict, Tuple

from lume_epics.client.controllers import Controller


DEFAULT_IMAGE_DATA = {
    "image": [np.zeros((50, 50))],
    "x": [50],
    "y": [50],
    "dw": [0.01],
    "dh": [0.01],
}

DEFAULT_SCALAR_VALUE = 0


class PVImage:
    """
    Object for updating and formatting image data.

    Attributes
    ----------
    prefix: str
        Server prefix

    variable: lume_model.variables.ImageVariable

    controller: online_model.app.widgets.controllers.Controller
        Controller object for getting pv values

    units: str
        Units associated with the variable

    pvname: str
        Name of the process variable to access.

    """

    def __init__(
        self,
        prefix: str,
        variable: lume_model.variables.ImageVariable,
        controller: Controller,
    ) -> None:
        """
        Initialize monitor with name and units.

        Parameters
        ----------
        prefix: str
            Server prefix

        variable: lume_model.variables.ImageVariable
            Image variable to display

        controller: lume_epics.client.controllers.Controller
            Controller object for getting pv values
        """
        self.units = None
        # check if units has been set
        if "units" in variable.__fields_set__:
            self.units = variable.units.split(":")

        self.pvname = f"{prefix}:{variable.name}"
        self.controller = controller
        self.axis_labels = variable.axis_labels
        self.axis_units = variable.axis_units

    def poll(self) -> Dict[str, list]:
        """
        Collects image data via appropriate protocol and builds image data dictionary.

        Returns
        -------
        dict
            Dictionary mapping image components to values.
        """

        try:
            value = self.controller.get_image(self.pvname)

        except TimeoutError:
            print(f"No process variable found for {self.pvname}")
            return DEFAULT_IMAGE_DATA

        return value


class PVTimeSeries:
    """
    Monitor for scalar process variables.

    Attributes
    ----------
    time: np.ndarray
        Array of sample times

    data: np.ndarray
        Array of data samples

    prefix: str
        Server prefix

    variable: lume_model.variables.Variable
        Variable to monitor for time series

    controller: online_model.app.widgets.controllers.Controller
        Controller object for getting pv values

    units: str
        Units associated with the variable

    pvname: str
        Name of the process variable to access

    """

    def __init__(
        self,
        prefix: str,
        variable: lume_model.variables.Variable,
        controller: Controller,
    ) -> None:
        """
        Initializes monitor attributes.

        Parameters
        ----------
        prefix: str
            Server prefix

        variable: lume_model.variables.Variable
            Variable to monitor for time series

        controller: online_model.app.widgets.controllers.Controller
            Controller object for getting pv values

        """
        self.pvname = pvname
        self.tstart = time.time()
        self.time = np.array([])
        self.data = np.array([])

        self.units = None
        # check if units has been set
        if "units" in variable.__fields_set__:
            self.units = variable.units

        self.pvname = f"{prefix}:{variable.name}"
        self.controller = controller

    def poll(self) -> Tuple[np.ndarray]:
        """
        Collects image data via appropriate protocol and returns time and data.

        Returns
        -------
        tuple
            (time, data)
        """
        t = time.time()
        try:
            v = self.controller.get(self.pvname)

        except TimeoutError:
            print(f"No process variable found for {self.pvname}")
            v = DEFAULT_SCALAR_VALUE

        self.time = np.append(self.time, t)
        self.data = np.append(self.data, v)
        return self.time - self.tstart, self.data


class PVScalar:
    """
    Monitor for scalar process variables.

    Attributes
    ----------
    prefix: str
        Server prefix

    variable: lume_model.variables.Variable
        Variable to monitor for time series

    controller: online_model.app.widgets.controllers.Controller
        Controller object for getting pv values

    units: str
        Units associated with the variable

    pvname: str
        Name of the process variable to access

    """

    def __init__(
        self,
        prefix: str,
        variable: lume_model.variables.Variable,
        controller: Controller,
    ) -> None:
        """
        Initializes monitor attributes.

        Parameters
        ----------
        prefix: str
            Server prefix

        variable: lume_model.variables.Variable
            Variable to monitor for time series

        controller: online_model.app.widgets.controllers.Controller
            Controller object for getting pv values
        """
        self.units = None
        # check if units has been set
        if "units" in variable.__fields_set__:
            self.units = variable.units
        self.pvname = f"{prefix}:{variable.name}"
        self.controller = controller

    def poll(self) -> Tuple[np.ndarray]:
        """
        Poll variable for value

        Returns
        -------
        Return value
        """
        try:
            v = self.controller.get(self.pvname)

        except TimeoutError:
            print(f"No process variable found for {self.pvname}")
            v = DEFAULT_SCALAR_VALUE

        return v
