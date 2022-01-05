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


# TODO: Track update dates per pv
# Check missing pvnames
# Update example


class Controller:
    """
    Controller class used to access process variables. Controllers are used for
    interfacing with both Channel Access and pvAccess process variables. The
    controller object is initialized using a single protocol has methods for
    both getting and setting values on the process variables.

    Attributes:
        _protocols (dict): Dictionary mapping pvname to protocol ("pva" for pvAccess, "ca" for
            Channel Access)

        _context (Context): P4P threaded context instance for use with pvAccess.

        _pv_registry (dict): Registry mapping pvname to dict of value and pv monitor


    Example:
        ```
        # create PVAcess controller
        controller = Controller("pva")

        value = controller.get_value("scalar_input")
        image_value = controller.get_image("image_input")

        controller.close()

        ```

    """

    def __init__(self, epics_config: dict):
        """
        Initializes controller. Stores protocol and creates context attribute if
        using pvAccess.

        Args:
            epics_config (dict): Dict describing epics configurations

        """
        self._pv_registry = defaultdict()
        # latest update
        self.last_update = ""

        # dictionary of last updates for all variables
        self._last_updates = {}
        self._epics_config = epics_config

        self._context = Context()

        ca_config = {
            var: {
                "pvname": self._epics_config[var]["pvname"],
                "serve": self._epics_config[var]["serve"],
            }
            for var in self._epics_config
            if self._epics_config[var]["protocol"] in ["ca", "both"]
        }
        pva_config = {
            var: {
                "pvname": self._epics_config[var]["pvname"],
                "serve": self._epics_config[var]["serve"],
            }
            for var in self._epics_config
            if self._epics_config[var]["protocol"] in ["pva", "both"]
        }

        if len(pva_config):
            self._context = Context("pva")

        # utility maps
        self._pvname_to_varname_map = {
            config["pvname"]: varname for varname, config in epics_config.items()
        }

        self._varname_to_pvname_map = {
            varname: config["pvname"] for varname, config in epics_config.items()
        }

        # track protocols
        self._protocols = {
            epics_config[variable]["pvname"]: epics_config[variable]["protocol"]
            for variable in epics_config
        }

    def _ca_value_callback(self, pvname, value, *args, **kwargs):
        """Callback executed by Channel Access monitor.

        Args:
            pvname (str): Process variable name

            value (Union[np.ndarray, float]): Value to assign to process variable.
        """
        self._pv_registry[pvname]["value"] = value

        update_datetime = datetime.now().strftime("%m/%d/%Y, %H:%M:%S")
        self.last_update = update_datetime
        self._last_updates[pvname] = update_datetime

    def _ca_connection_callback(self, *, pvname, conn, pv):
        """Callback used for monitoring connection and setting values to None on disconnect.
        """
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

        update_datetime = datetime.now().strftime("%m/%d/%Y, %H:%M:%S")
        self.last_update = update_datetime
        self._last_updates[pvname] = update_datetime

    def _set_up_pv_monitor(self, pvname, root=None):
        """Set up process variable monitor.

        Args:
            pvname (str): Process variable name

        """
        if pvname in self._pv_registry:
            return

        if root:
            protocol = self._protocols[root]

        else:
            protocol = self._protocols[pvname]

        if protocol == "ca":

            # add to registry (must exist for connection callback)
            self._pv_registry[pvname] = {"pv": None, "value": None}

            # create the pv
            pv_obj = PV(
                pvname,
                callback=self._ca_value_callback,
                connection_callback=self._ca_connection_callback,
            )

            # update registry
            self._pv_registry[pvname]["pv"] = pv_obj

        elif protocol == "pva":
            cb = partial(self._pva_value_callback, pvname)
            # populate registry s.t. initially disconnected will populate
            self._pv_registry[pvname] = {"pv": None, "value": None}

            # create the monitor obj
            mon_obj = self._context.monitor(pvname, cb, notify_disconnect=True)

            # update registry with the monitor
            self._pv_registry[pvname]["pv"] = mon_obj

    def get(self, pvname: str, root: str = None) -> np.ndarray:
        """
        Accesses and returns the value of a process variable.

        Args:
            varname (str): Model variable name

        """
        self._set_up_pv_monitor(pvname, root=root)

        pv = self._pv_registry.get(pvname, None)

        if pv:
            return pv["value"]

        return None

    def get_value(self, varname):
        """Gets scalar value of a process variable.

        Args:
            varname (str): Model variable name

        """
        pvname = self._get_pvname(varname)
        value = self.get(pvname)

        if value is None:
            value = DEFAULT_SCALAR_VALUE

        return value

    def get_image(self, varname) -> dict:
        """Gets image data via controller protocol.

        Args:
            varname (str): Model variable name

        """
        pvname = self._get_pvname(varname)
        image = None
        if self._protocols[pvname] == "ca":
            image_flat = self.get(f"{pvname}:ArrayData_RBV", root=pvname)
            nx = self.get(f"{pvname}:ArraySizeX_RBV", root=pvname)
            ny = self.get(f"{pvname}:ArraySizeY_RBV", root=pvname)
            x = self.get(f"{pvname}:MinX_RBV", root=pvname)
            y = self.get(f"{pvname}:MinY_RBV", root=pvname)
            x_max = self.get(f"{pvname}:MaxX_RBV", root=pvname)
            y_max = self.get(f"{pvname}:MaxY_RBV", root=pvname)

            if all(
                [
                    image_def is not None
                    for image_def in [image_flat, nx, ny, x, y, x_max, y_max]
                ]
            ):
                dw = x_max - x
                dh = y_max - y

                image = image_flat.reshape(int(nx), int(ny))

        elif self._protocols[pvname] == "pva":
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

    def get_array(self, varname) -> dict:
        """Gets array data via controller protocol.

        Args:
            varname (str): Model variable name

        """
        pvname = self._get_pvname(varname)
        array = None
        if self._protocols[pvname] == "ca":
            array_flat = self.get(f"{pvname}:ArrayData_RBV", root=pvname)
            shape = self.get(f"{pvname}:ArraySize_RBV", root=pvname)

            if all([array_def is not None for array_def in [array_flat, shape]]):

                array = np.array(array_flat).reshape(shape)

        elif self._protocols[pvname] == "pva":
            # context returns numpy array with WRITEABLE=False
            # copy to manipulate array below

            array = self.get(pvname)

        if array is not None:
            return array
        else:
            return np.array([])

    def put(self, varname, value: float, timeout=1.0) -> None:
        """Assign the value of a scalar process variable.

        Args:
            varname (str): Model variable name

            value (float): Value to assing to process variable.

            timeout (float): Operation timeout in seconds

        """
        pvname = self._get_pvname(varname)
        self._set_up_pv_monitor(pvname)

        # allow no puts before a value has been collected
        registered = self.get(pvname)

        # if the value is registered
        if registered is not None:
            if self._protocols[pvname] == "ca":
                self._pv_registry[pvname]["pv"].put(value, timeout=timeout)

            elif self._protocols[pvname] == "pva":
                self._context.put(pvname, value, throw=False, timeout=timeout)

        else:
            logger.debug(f"No initial value set for {pvname}.")

    def put_image(
        self,
        varname,
        image_array: np.ndarray = None,
        x_min: float = None,
        x_max: float = None,
        y_min: float = None,
        y_max: float = None,
        timeout: float = 1.0,
    ) -> None:
        """Assign the value of a image process variable. Allows updates to individual attributes.

        Args:
            varname (str): Model variable name

            image_array (np.ndarray): Value to assing to process variable.

            x_min (float): Minimum x value

            x_max (float): Maximum x value

            y_min (float): Minimum y value

            y_max (float): Maximum y value

            timeout (float): Operation timeout in seconds

        """
        pvname = self._get_pvname(varname)
        self._set_up_pv_monitor(pvname, root=pvname)

        # allow no puts before a value has been collected
        registered = self.get_image(pvname)

        # if the value is registered
        if registered is not None:
            if self._protocols[pvname] == "ca":

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

            elif self._protocols[pvname] == "pva":

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
        self, varname, array: np.ndarray = None, timeout: float = 1.0,
    ) -> None:
        """Assign the value of an array process variable. Allows updates to individual attributes.

        Args:
            varname (str): Model variable name

            array (np.ndarray): Value to assing to process variable.

            timeout (float): Operation timeout in seconds

        """
        pvname = self._get_pvname(varname)
        self._set_up_pv_monitor(pvname, root=pvname)

        # allow no puts before a value has been collected
        registered = self.get_array(pvname)

        # if the value is registered
        if registered is not None:
            if self._protocols[pvname] == "ca":

                if array is not None:
                    self._pv_registry[f"{pvname}:ArrayData_RBV"]["pv"].put(
                        array.flatten(), timeout=timeout
                    )

            elif self._protocols[pvname] == "pva":

                # compose normative type
                pv = self._pv_registry[pvname]
                array = pv["value"]

                self._context.put(pvname, array, throw=False, timeout=timeout)

        else:
            logger.debug(f"No initial value set for {pvname}.")

    def close(self):
        if self._context is not None:
            self._context.close()

    def _get_pvname(self, varname):

        pvname = self._varname_to_pvname_map.get(varname)
        if not pvname:
            raise ValueError(
                f"{varname} has not been configured with EPICS controller."
            )

        else:
            return pvname
