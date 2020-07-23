"""
Controllers are used for interfacing with both Channel Access and PVAccess process
variables. The controller object is initialized using a single protocol has methods for
both getting and setting values on the process variables.

"""
from typing import Union
import numpy as np
import copy
import logging

from epics import caget, caput
from p4p.client.thread import Context

logger = logging.getLogger(__name__)

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
    Controller class used access process variables.

    Attributes:
        protocol (str): Protocol for accessing variables ("pva" for PVAccess, "ca" for
            Channel Access)

        context (Context): P4P threaded context instance for use with PVAccess.

    """

    def __init__(self, protocol: str):
        """
        Initializes controller. Stores protocol and creates context attribute if 
        using PVAccess.
        """
        self.protocol = protocol

        # initalize context for pva
        self.context = None
        if protocol == "pva":
            self.context = Context("pva")

    def get(self, pvname: str) -> np.ndarray:
        """
        Accesses and returns the value of a process variable.

        Args:
            pvname (str): Process variable name

        """
        try:
            if self.protocol == "ca":
                value = caget(pvname)

            elif self.protocol == "pva":
                value = self.context.get(pvname)

        except TimeoutError:
            logger.exception("Unable to connect to process variable %s using protocol %s", pvname, self.protocol)
            value = None

        return value

    def get_value(self, pvname):
        """Gets scalar value of a process variable.

        Args:
            pvname (str): Image process variable name

        """
        value = self.get(pvname)

        if value is None:
            value = DEFAULT_SCALAR_VALUE

        return value

    def get_image(self, pvname) -> dict:
        """Gets image data via protocol.

        Args:
            pvname (str): Image process variable name

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
            # context returns numpy array with WRITEABLE=False
            # copy to manipulate array below
            image = self.get(pvname)

            if image is not None:
                attrib = image.attrib
                x = attrib["x_min"]
                y = attrib["y_min"]
                dw = attrib["x_max"]
                dh = attrib["y_max"]
                image = copy.copy(image)

        if image is not None:
            return {
                "image": [image],
                "x": [x],
                "y": [y],
                "dw": [dw],
                "dh": [dh],
            }

        else:
            return DEFAULT_IMAGE_DATA


    def put(self, pvname, value: Union[np.ndarray, float]) -> None:
        """Assign the value of a process variable.

        Args:
            pvname (str): Name of the process variable

            value (Union[np.ndarray, float]): Value to assing to process variable.

        """
        if self.protocol == "ca":
            caput(pvname, value)

        elif self.protocol == "pva":
            self.context.put(pvname, value)

    def close(self):
        if self.protocol == "pva":
            self.context.close()
