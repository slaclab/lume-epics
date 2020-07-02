from typing import Union
import numpy as np
import copy
from epics import caget, caput
from p4p.client.thread import Context

DEFAULT_IMAGE_DATA = {
    "image": [np.zeros((50, 50))],
    "x": [50],
    "y": [50],
    "dw": [0.01],
    "dh": [0.01],
}

DEFAULT_SCALAR_VALUE = 0


class Controller:
    """
    Controller class used to get and put process variables.

    Attributes
    ----------
    protocol: str
        Protocol to use ("pva", "ca")

    context: p4p.client.thread.Context
        p4p threaded context instance

    """

    def __init__(self, protocol: str):
        """
        Store protocol and initialize context if using PVAccess.
        """
        self.protocol = protocol

        # initalize context for pva
        self.context = None
        if protocol == "pva":
            self.context = Context("pva")

    def get(self, pvname: str):
        """
        Get the value of a process variable.

        Parameters
        ----------
        pvname: str
            Name of the process variable

        Returns
        -------
        np.ndarray
            Returns numpy array containing value.

        """
        try:
            if self.protocol == "ca":
                value = caget(pvname)

            elif self.protocol == "pva":
                value = self.context.get(pvname)

        except TimeoutError:
            print(f"Unable to connect to process variable {pvname}")
            value = None

        return value

    def get_value(self, pvname):
        value = self.get(pvname)

        if value is None:
            value = DEFAULT_SCALAR_VALUE

        return value

    def get_image(self, pvname):
        """
        Gets image data based on protocol.

        Parameters
        ----------
        pvname: str
            Name of process variable

        Returns
        -------
        dict
            Formatted image data of the form
            ```
                {
                "image": [np.ndarray],
                "x": [float],
                "y": [float],
                "dw": [float],
                "dh": [float],
            }
            ```
        """

        if self.protocol == "ca":
            image = self.get(f"{pvname}:ArrayData_RBV")

            if image is not None:
                pvbase = pvname.replace(":ArrayData_RBV", "")
                nx = self.get(f"{pvbase}:ArraySizeX_RBV")
                ny = self.get(f"{pvbase}:ArraySizeY_RBV")
                x = self.get(f"{pvbase}:MinX_RBV")
                y = self.get(f"{pvbase}:MinY_RBV")
                dw = self.get(f"{pvbase}:MaxX_RBV")
                dh = self.get(f"{pvbase}:MaxY_RBV")

                image = image.reshape(int(nx), int(ny))

        elif self.protocol == "pva":
            # context returns np array with WRITEABLE=False
            # copy to manipulate array below
            image = self.get(pvname)

            if image is not None:
                attrib = image.attrib
                x = attrib["x_min"]
                y = attrib["y_min"]
                dw = attrib["x_max"]
                dh = attrib["y_max"]
                image = copy.copy(image)

        if image:
            return {
                "image": [image],
                "x": [x],
                "y": [y],
                "dw": [dw],
                "dh": [dh],
            }

        else:
            return DEFAULT_IMAGE_DATA

    #     print(f"No value found for {pvname}")
    #     return DEFAULT_IMAGE_DATA

    def put(self, pvname, value: Union[np.ndarray, float]) -> None:
        """
        Assign the value of a process variable.

        Parameters
        ----------
        pvname: str
            Name of the process variable

        value
            Value to put. Either float or numpy array

        """
        if self.protocol == "ca":
            caput(pvname, value)

        elif self.protocol == "pva":
            self.context.put(pvname, value)

    def close(self):
        if self.protocol == "pva":
            self.context.close()
