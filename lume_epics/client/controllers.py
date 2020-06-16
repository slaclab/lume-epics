from typing import Union
import numpy as np
import copy
from epics import caget, caput
from p4p.client.thread import Context


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
        if self.protocol == "ca":
            return caget(pvname)

        elif self.protocol == "pva":
            return self.context.get(pvname)

    def get_image(self, pvname):
        """
        Gets image data based on protocol.

        Arguments
        ---------
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
            pvname = pvname.replace(":ArrayData_RBV", "")
            nx = self.get(f"{pvname}:ArraySizeX_RBV")
            ny = self.get(f"{pvname}:ArraySizeY_RBV")
            dw = self.get(f"{pvname}:dw")
            dh = self.get(f"{pvname}:dh")
            image = self.get(f"{pvname}:ArrayData_RBV")
            image = image.reshape(int(nx), int(ny))

        elif self.protocol == "pva":
            # context returns np array with WRITEABLE=False
            # copy to manipulate array below
            output = self.get(pvname)
            attrib = output.attrib
            dw = attrib["dw"]
            dh = attrib["dh"]
            nx, ny = output.shape
            image = copy.copy(output)

        return {
            "image": [image],
            "x": [-dw / 2],
            "y": [-dh / 2],
            "dw": [dw],
            "dh": [dh],
        }

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
