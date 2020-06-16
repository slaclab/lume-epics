import time

import numpy as np
from typing import List, Dict, Tuple

from online_model.app.controllers import Controller


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
    pvname: str
        Process variable name

    units: str
        Units for process variable

    """

    def __init__(self, pvname: str, units: str, controller: Controller) -> None:
        """
        Initialize monitor with name and units.

        Parameters
        ----------
        pvname: str
            Name of the process variable

        units: str
            Unit label of the variable

        controller: online_model.app.widgets.controllers.Controller
            Controller object for getting pv values
        """
        self.units = units.split(":")
        self.pvname = pvname
        self.controller = controller

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

        # now prepare the value using method defined by the model
        return value

    def variables(self) -> List[str]:
        """
        Returns variables to be plotted. 'x:y' -> ['x', 'y']
        """
        return self.pvname.split(":")


class PVTimeSeries:
    """
    Monitor for scalar process variables.

    Attributes
    ----------
    tstart:

    time: np.ndarray
        Array of sample times

    data: np.ndarray
        Array of data samples
    """

    def __init__(self, pvname: str, units: str, controller: Controller) -> None:
        """
        Initializes monitor attributes.

        Parameters
        ----------
        pvname: str
            Process variable name

        units: str
            Units for process variable

        controller: online_model.app.widgets.controllers.Controller
            Controller object for getting pv values

        """
        self.pvname = pvname
        self.tstart = time.time()
        self.time = np.array([])
        self.data = np.array([])
        self.units = units.split(":")
        self.controller = controller

    def poll(self) -> Tuple[np.ndarray]:
        """
        Collects image data via appropriate protocol and returns time and data.
        """
        t = time.time()
        try:
            v = self.controller.get(self.pvname)

        except TimeoutError:
            print(f"No process variable found for {self.pvname}")
            v = DEFAULT_SCALAR_VALUE[self.pvname]

        self.time = np.append(self.time, t)
        self.data = np.append(self.data, v)

        return self.time - self.tstart, self.data


class PVScalar:
    """
    Monitor for scalar process variables.

    Attributes
    ----------
    """

    def __init__(self, pvname: str, units: str, controller: Controller) -> None:
        """
        Initializes monitor attributes.

        Parameters
        ----------
        pvname: str
            Process variable name

        units: str
            Units for process variable

        controller: online_model.app.widgets.controllers.Controller
            Controller object for getting pv values

        """
        self.units = units.split(":")
        self.pvname = pvname
        self.controller = controller

    def poll(self) -> Tuple[np.ndarray]:
        """
        Collects image data via appropriate protocol and returns time and data.
        """
        try:
            v = self.controller.get(self.pvname)

        except TimeoutError:
            print(f"No process variable found for {self.pvname}")
            v = DEFAULT_SCALAR_VALUE

        return v
