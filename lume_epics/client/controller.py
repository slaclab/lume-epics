"""
The lume-epics controller serves as the intermediary between variable monitors 
and process variables served over EPICS.
"""
from typing import Union
import numpy as np
import copy
import logging
from collections import defaultdict
from functools import partial 
from epics import PV
import threading
import sys
from p4p.client.thread import Context, Disconnected


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
    Controller class used to access process variables. Controllers are used for 
    interfacing with both Channel Access and pvAccess process variables. The 
    controller object is initialized using a single protocol has methods for
    both getting and setting values on the process variables.

    Attributes:
        protocol (str): Protocol for getting values from variables ("pva" for pvAccess, "ca" for
            Channel Access)

        context (Context): P4P threaded context instance for use with pvAccess.

        set_ca (bool): Update Channel Access variable on put.

        set_pva (bool): Update pvAccess variable on put.

        pv_registry (dict): Registry mapping pvname to dict of value and pv monitor

    Example:
        ```
        # create PVAcess controller
        controller = Controller("pva")

        value = controller.get_value("scalar_input")
        image_value = controller.get_image("image_input")

        controller.close()

        ```

    """

    def __init__(self, protocol: str):
        """
        Initializes controller. Stores protocol and creates context attribute if 
        using pvAccess.

        Args: 
            protocol (str): Protocol for getting values from variables ("pva" for pvAccess, "ca" for
            Channel Access)

        """
        self.protocol = protocol
        self.pv_registry = defaultdict()

        # initalize context for pva
        self.context = None
        if self.protocol == "pva":
            self.context = Context("pva")


    def ca_value_callback(self, pvname, value, *args, **kwargs):
        """Callback executed by Channel Access monitor.

        Args:
            pvname (str): Process variable name

            value (Union[np.ndarray, float]): Value to assign to process variable.
        """
        self.pv_registry[pvname]["value"] = value


    def ca_connection_callback(self, *, pvname, conn, pv):
        """Callback used for monitoring connection and setting values to None on disconnect.
        """
        # if disconnected, set value to None
        if not conn:
            self.pv_registry[pvname]["value"] = None


    def pva_value_callback(self, pvname, value):
        """Callback executed by pvAccess monitor.

        Args:
            pvname (str): Process variable name

            value (Union[np.ndarray, float]): Value to assign to process variable.
        """
        if isinstance(value, Disconnected):
            self.pv_registry[pvname]["value"] = None
        else:
            self.pv_registry[pvname]["value"] = value


    def setup_pv_monitor(self, pvname):
        """Set up process variable monitor.

        Args:
            pvname (str): Process variable name

        """
        if pvname in self.pv_registry:
            return

        if self.protocol == "ca":
            # add to registry (must exist for connection callback)
            self.pv_registry[pvname] = {"pv": None, "value": None}

            # create the pv
            pv_obj = PV(pvname, callback=self.ca_value_callback, connection_callback=self.ca_connection_callback)

            # update registry
            self.pv_registry[pvname]["pv"] = pv_obj

        elif self.protocol == "pva":
            cb = partial(self.pva_value_callback, pvname)
            # populate registry s.t. initially disconnected will populate
            self.pv_registry[pvname] = {"pv": None, "value": None}

            # create the monitor obj
            mon_obj = self.context.monitor(pvname, cb, notify_disconnect=True)
            
            # update registry with the monitor
            self.pv_registry[pvname]["pv"] = mon_obj


    def get(self, pvname: str) -> np.ndarray:
        """
        Accesses and returns the value of a process variable.

        Args:
            pvname (str): Process variable name

        """
        self.setup_pv_monitor(pvname)
        pv = self.pv_registry.get(pvname, None)
        if pv:
            #return pv.get("value", None)
            return pv["value"]
        return None


    def get_value(self, pvname):
        """Gets scalar value of a process variable.

        Args:
            pvname (str): Image process variable name.

        """
        value = self.get(pvname)

        if value is None:
            value = DEFAULT_SCALAR_VALUE

        return value


    def get_image(self, pvname) -> dict:
        """Gets image data via controller protocol.

        Args:
            pvname (str): Image process variable name

        """
        image = None
        if self.protocol == "ca":
            image_flat = self.get(f"{pvname}:ArrayData_RBV")
            nx = self.get(f"{pvname}:ArraySizeX_RBV")
            ny = self.get(f"{pvname}:ArraySizeY_RBV")
            x = self.get(f"{pvname}:MinX_RBV")
            y = self.get(f"{pvname}:MinY_RBV")
            x_max = self.get(f"{pvname}:MaxX_RBV")
            y_max = self.get(f"{pvname}:MaxY_RBV")

            if all([image_def is not None for image_def in [image_flat, nx, ny, x, y, x_max, y_max]]):
                dw = x_max - x
                dh = y_max - y

                image = image_flat.reshape(int(nx), int(ny))

        elif self.protocol == "pva":
            # context returns numpy array with WRITEABLE=False
            # copy to manipulate array below

            image = self.get(pvname)

            if image is not None:
                attrib = image.attrib
                x = attrib["x_min"]
                y = attrib["y_min"]
                dw = attrib["x_max"] - attrib["x_min"]
                dh = attrib["y_max"] - attrib["y_min"]
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


    def put(self, pvname, value: Union[np.ndarray, float], timeout=1.0) -> None:
        """Assign the value of a process variable.

        Args:
            pvname (str): Name of the process variable

            value (Union[np.ndarray, float]): Value to assing to process variable.

            timeout (float): Operation timeout in seconds

        """
        self.setup_pv_monitor(pvname)

        # allow no puts before a value has been collected
        registered = self.get(pvname)

        # if the value is registered
        if registered is not None:
            if self.protocol == "ca":
                self.pv_registry[pvname]["pv"].put(value, timeout=timeout)

            elif self.protocol == "pva":
                self.context.put(pvname, value, throw=False, timeout=timeout)

        else:
            logger.debug(f"No initial value set for {pvname}.")

    def close(self):
        if self.protocol == "pva":
            self.context.close()
