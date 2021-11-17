"""
The lume-epics controller serves as the intermediary between variable monitors
and process variables served over EPICS.
"""
from typing import Union, List
import numpy as np
import copy
import logging
from datetime import datetime
from collections import defaultdict
from functools import partial

from epics import PV, caget
import threading
import sys
from p4p.client.thread import Context, Disconnected
import os

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
        _protocol (str): Protocol for getting values from variables ("pva" for pvAccess, "ca" for
            Channel Access)

        _context (Context): P4P threaded context instance for use with pvAccess.

        _pv_registry (dict): Registry mapping pvname to dict of value and pv monitor

        _input_pvs (dict): Dictionary of input process variables

        _output_pvs (dict): Dictionary out output process variables

        _prefix (str): Prefix to use for accessing variables

        last_input_update (datetime): Last update of input variables

        last_output_update (datetime): Last update of output variables

    Example:
        ```
        # create PVAcess controller
        controller = Controller("pva")

        value = controller.get_value("scalar_input")
        image_value = controller.get_image("image_input")

        controller.close()

        ```

    """

    def __init__(
        self,
        protocol: str,
        input_pvs: dict,
        output_pvs: dict,
        prefix=None,
        auto_monitor=True,
    ):
        """
        Initializes controller. Stores protocol and creates context attribute if
        using pvAccess.

        Args:
            protocol (str): Protocol for getting values from variables ("pva" for pvAccess, "ca" for
            Channel Access)

            input_pvs (dict): Dict mapping input variable names to variable

            output_pvs (dict): Dict mapping output variable names to variable

            prefix (str): String prefix for fetching pvs

            auto_monitor (bool): Indicate whether to use subscriptions for values

        """
        self._protocol = protocol
        self._pv_registry = defaultdict()
        self._input_pvs = input_pvs
        self._output_pvs = output_pvs
        self._prefix = prefix
        self.last_input_update = ""
        self.last_output_update = ""
        self._auto_monitor = auto_monitor
        self._pvnames = {}

        # initalize context for pva
        self._context = None
        if self._protocol == "pva":
            self._context = Context("pva")

        # initialize controller
        for variable in {**input_pvs, **output_pvs}.values():
            if prefix:
                pvname = f"{prefix}:{variable.name}"

            else:
                pvname = variable.name
            #  self._pvnames[variable.name] = variable.name

            if variable.variable_type == "image":
                for image_el in [
                    "ArrayData_RBV",
                    "ArraySizeX_RBV",
                    "ArraySizeY_RBV",
                    "MinX_RBV",
                    "MinY_RBV",
                    "MaxX_RBV",
                    "MaxY_RBV",
                ]:
                    self._pvnames[
                        f"{variable.name}:{image_el}"
                    ] = f"{pvname}:{image_el}"

                self.get_image(variable.name)

            elif variable.variable_type == "array":
                self._pvnames[variable.name] = pvname
                self.get_array(variable.name)

            else:
                self._pvnames[variable.name] = pvname
                self.get_value(variable.name)

    def _ca_value_callback(self, pvname, value, *args, **kwargs):
        """Callback executed by Channel Access monitor.

        Args:
            pvname (str): Process variable name

            value (Union[np.ndarray, float]): Value to assign to process variable.
        """
        pvname = pvname.replace(f"{self._prefix}:", "")
        self._pv_registry[pvname]["value"] = value

        if pvname in self._input_pvs:
            self.last_input_update = datetime.now().strftime("%m/%d/%Y, %H:%M:%S")

        if pvname in self._output_pvs:
            self.last_output_update = datetime.now().strftime("%m/%d/%Y, %H:%M:%S")

    def _ca_connection_callback(self, *, pvname, conn, pv):
        """Callback used for monitoring connection and setting values to None on disconnect.
        """
        # if disconnected, set value to None
        pvname = pvname.replace(f"{self._prefix}:", "")

        if not conn:
            self._pv_registry[pvname]["value"] = None

    def _pva_value_callback(self, pvname, value):
        """Callback executed by pvAccess monitor.

        Args:
            pvname (str): Process variable name

            value (Union[np.ndarray, float]): Value to assign to process variable.
        """
        if isinstance(value, Disconnected):
            self._pv_registry[pvname]["value"] = None
        else:
            self._pv_registry[pvname]["value"] = value

        if pvname in self._input_pvs:
            self.last_input_update = datetime.now().strftime("%m/%d/%Y, %H:%M:%S")

        if pvname in self._output_pvs:
            self.last_output_update = datetime.now().strftime("%m/%d/%Y, %H:%M:%S")

    def _register(self, pvname):
        """Set up process variable monitor.

        Args:
            pvname (str): Process variable name

        """
        if pvname in self._pv_registry:
            return

        if self._protocol == "ca":
            # add to registry (must exist for connection callback)
            self._pv_registry[pvname] = {"pv": None, "value": None}

            # create the pv
            if self._auto_monitor:
                pv_obj = PV(
                    self._pvnames[pvname],
                    callback=self._ca_value_callback,
                    connection_callback=self._ca_connection_callback,
                )

            else:
                pv_obj = PV(
                    self._pvnames[pvname],
                    connection_callback=self._ca_connection_callback,
                )

            # update registry
            self._pv_registry[pvname]["pv"] = pv_obj

        elif self._protocol == "pva":
            # populate registry s.t. initially disconnected will populate
            self._pv_registry[pvname] = {"pv": None, "value": None}

            if self._auto_monitor:
                cb = partial(self._pva_value_callback, pvname)

                # create the monitor obj
                mon_obj = self._context.monitor(
                    self._pvnames[pvname], cb, notify_disconnect=True
                )

                # update registry with the monitor
                self._pv_registry[pvname]["pv"] = mon_obj

    def get(self, pvname: str) -> np.ndarray:
        """
        Accesses and returns the value of a process variable.

        Args:
            pvname (str): Process variable name

        """
        self._register(pvname)

        if self._auto_monitor:
            pv = self._pv_registry.get(pvname, None)

            if pv:
                return pv["value"]

        else:
            if self._protocol == "pva":
                return self._context.get(self._pvnames[pvname])

            elif self._protocol == "ca":
                pv = self._pv_registry.get(pvname, None)

                if pv:
                    try:
                        val = pv["pv"].get(timeout=0.5)
                        return val
                    except:
                        logger.error(f"unable to get {pvname}")

        return None

    def get_value(self, pvname):
        """Gets scalar value of a process variable.

        Args:
            pvname (str): Process variable name.

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
        if self._protocol == "ca":
            image_flat = self.get(f"{pvname}:ArrayData_RBV")
            nx = self.get(f"{pvname}:ArraySizeX_RBV")
            ny = self.get(f"{pvname}:ArraySizeY_RBV")
            x = self.get(f"{pvname}:MinX_RBV")
            y = self.get(f"{pvname}:MinY_RBV")
            x_max = self.get(f"{pvname}:MaxX_RBV")
            y_max = self.get(f"{pvname}:MaxY_RBV")

            if all(
                [
                    image_def is not None
                    for image_def in [image_flat, nx, ny, x, y, x_max, y_max]
                ]
            ):
                dw = x_max - x
                dh = y_max - y

                image = image_flat.reshape(int(nx), int(ny))

        elif self._protocol == "pva":
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

    def get_array(self, pvname) -> dict:
        """Gets array data via controller protocol.

        Args:
            pvname (str): Image process variable name

        """
        array = None
        if self._protocol == "ca":
            array_flat = self.get(f"{pvname}:ArrayData_RBV")
            shape = self.get(f"{pvname}:ArraySize_RBV")

            if all([array_def is not None for array_def in [array_flat, shape]]):

                array = np.array(array_flat).reshape(shape)

        elif self._protocol == "pva":
            # context returns numpy array with WRITEABLE=False
            # copy to manipulate array below

            array = self.get(pvname)

        if array is not None:
            return array
        else:
            return np.array([])

    def put(self, pvname, value: float, timeout=1.0) -> None:
        """Assign the value of a scalar process variable.

        Args:
            pvname (str): Name of the process variable

            value (float): Value to assign to process variable.

            timeout (float): Operation timeout in seconds

        """
        self._register(pvname)

        # allow no puts before a value has been collected
        registered = self.get(pvname)

        # if the value is registered
        if registered is not None:
            if self._protocol == "ca":
                self._pv_registry[pvname]["pv"].put(value, timeout=timeout)

            elif self._protocol == "pva":
                self._context.put(
                    self._pvnames[pvname], value, throw=False, timeout=timeout
                )

        else:
            logger.debug(f"No initial value set for {pvname}.")

    def put_image(
        self,
        pvname,
        image_array: np.ndarray = None,
        x_min: float = None,
        x_max: float = None,
        y_min: float = None,
        y_max: float = None,
        timeout: float = 1.0,
    ) -> None:
        """Assign the value of a image process variable. Allows updates to individual attributes.

        Args:
            pvname (str): Name of the process variable

            image_array (np.ndarray): Value to assing to process variable.

            x_min (float): Minimum x value

            x_max (float): Maximum x value

            y_min (float): Minimum y value

            y_max (float): Maximum y value

            timeout (float): Operation timeout in seconds

        """
        self._register(pvname)

        # allow no puts before a value has been collected
        registered = self.get_image(pvname)

        # if the value is registered
        if registered is not None:
            if self._protocol == "ca":

                if image_array is not None:
                    self._pv_registry[f"{pvname}:ArrayData_RBV"]["pv"].put(
                        image_array.flatten(), timeout=timeout
                    )

                if x_min:
                    self._pv_registry[f"{pvname}:MinX_RBV"]["pv"].put(
                        x_min, timeout=timeout
                    )

                if x_max:
                    self._pv_registry[f"{pvname}:MaxX_RBV"]["pv"].put(
                        x_max, timeout=timeout
                    )

                if y_min:
                    self._pv_registry[f"{pvname}:MinY_RBV"]["pv"].put(
                        y_min, timeout=timeout
                    )

                if y_max:
                    self._pv_registry[f"{pvname}:MaxY_RBV"]["pv"].put(
                        y_max, timeout=timeout
                    )

            elif self._protocol == "pva":

                # compose normative type
                pv = self._pv_registry[pvname]
                pv_array = pv["value"]

                if image_array:
                    image_array.attrib = pv_array.attrib

                else:
                    image_array = pv_array

                if x_min:
                    image_array.attrib.x_min = x_min

                if x_max:
                    image_array.attrib.x_max = x_max

                if y_min:
                    image_array.attrib.y_min = y_min

                if y_max:
                    image_array.attrib.y_max = y_max

                self._context.put(pvname, image_array, throw=False, timeout=timeout)

        else:
            logger.debug(f"No initial value set for {pvname}.")

    def put_array(
        self, pvname, array: np.ndarray = None, timeout: float = 1.0,
    ) -> None:
        """Assign the value of an array process variable. Allows updates to individual attributes.

        Args:
            pvname (str): Name of the process variable

            array (np.ndarray): Value to assing to process variable.

            timeout (float): Operation timeout in seconds

        """
        self._register(pvname)

        # allow no puts before a value has been collected
        registered = self.get_array(pvname)

        # if the value is registered
        if registered is not None:
            if self._protocol == "ca":

                if array is not None:
                    self._pv_registry[f"{pvname}:ArrayData_RBV"]["pv"].put(
                        array.flatten(), timeout=timeout
                    )

            elif self._protocol == "pva":

                # compose normative type
                pv = self._pv_registry[pvname]
                array = pv["value"]

                self._context.put(pvname, array, throw=False, timeout=timeout)

        else:
            logger.debug(f"No initial value set for {pvname}.")

    def close(self):
        if self._protocol == "pva":
            self._context.close()
