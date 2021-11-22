"""
Monitors interface with widgets to surface process variable information. They are
initialized using a lume-model variable and a controller used to access values over
EPICs.

"""

from datetime import datetime
import time
import logging
import copy
import numpy as np
from typing import List, Dict, Tuple

from lume_epics.client.controller import Controller
from lume_model.variables import (
    ImageVariable,
    ScalarVariable,
    TableVariable,
    ArrayVariable,
)

logger = logging.getLogger(__name__)


class PVImage:
    """
    Monitor for updating and formatting image data.

    Attributes:
        variable (ImageVariable): Image process variable to be displayed.

        controller (Controller): Controller object for accessing process variable.

        pvname (str): Name of the process variable to access.

        axis_units (str): Units associated with the image axes.

        axis_labels (str): Labels associated with the image axes.

    """

    def __init__(self, variable: ImageVariable, controller: Controller,) -> None:
        """Initialize monitor for an image variable.

        Args:
            variable (ImageVariable): Image process variable to be displayed.

            controller (Controller): Controller object for accessing process variable.

        """
        self.units = None
        # check if units has been set
        if "units" in variable.__fields_set__:
            self.units = variable.units.split(":")

        self.pvname = variable.name
        self.controller = controller
        self.axis_labels = variable.axis_labels
        self.axis_units = variable.axis_units

    def poll(self) -> Dict[str, list]:
        """Collects image data and builds image data dictionary.

        """

        return self.controller.get_image(self.pvname)


class PVTimeSeries:
    """
    Monitor for time series variables.

    Attributes:
        time (np.ndarray): Array of times sampled.

        data (np.ndarray): Array of sampled data.

        variable (ScalarVariable): Variable monitored for time series.

        controller (Controller): Controller object for accessing process variable.

        units (str): Units associated with the variable

        pvname (str): Name of the process variable to access

    """

    def __init__(self, variable: ScalarVariable, controller: Controller,) -> None:
        """Initializes monitor attributes.

        Args:
            variable (ScalarVariable): Variable to monitor for time series

            controller (Controller): Controller object for accessing process variable.

        """
        self.pvname = variable.name
        self.tstart = time.time()
        self.time = np.array([])
        self.data = np.array([])

        self.units = None
        # check if units has been set
        if "units" in variable.__fields_set__:
            self.units = variable.units

        self.controller = controller

    def poll(self) -> Tuple[np.ndarray]:
        """
        Collects image data via appropriate protocol and returns time and data.

        """
        t = datetime.now()

        v = self.controller.get_value(self.pvname)

        self.time = np.append(self.time, t)
        self.data = np.append(self.data, v)

        return self.time, self.data

    def reset(self) -> None:
        self.time = np.array([])
        self.data = np.array([])


class PVScalar:
    """
    Monitor for scalar process variables.

    Attributes:
        variable (ScalarVariable): Variable to monitor for value.

        controller (Controller): Controller object for accessing process variable.

        units (str): Units associated with the variable.

        pvname (str): Name of the process variable to access.

    """

    def __init__(self, variable: ScalarVariable, controller: Controller,) -> None:
        """Initializes monitor attributes.

        Args:
            variable (ScalarVariable):  Variable to monitor for value.

            controller (Controller): Controller object for accessing process variable.
        """
        self.units = None
        # check if units has been set
        if "units" in variable.__fields_set__:
            self.units = variable.units
        self.pvname = variable.name
        self.controller = controller

    def poll(self) -> Tuple[np.ndarray]:
        """
        Poll variable for value,

        """
        return self.controller.get_value(self.pvname)


class PVTable:
    """
    Monitor for pvs organized as table

    Attributes:
        variable (ScalarVariable): Variable to monitor for value.

        controller (Controller): Controller object for accessing process variable.

        units (str): Units associated with the variable.

        pvname (str): Name of the process variable to access.

    """

    def __init__(self, variable: TableVariable, controller: Controller,) -> None:
        """Initializes monitor attributes.

        Args:
            variable (ScalarVariable):  Variable to monitor for value.

            controller (Controller): Controller object for accessing process variable.
        """
        self._table_variable = variable
        self._composing_variables = []
        # table map shows how values are represented column, row structure
        self.data = {}
        self.output_structure = {}

        for col, row_val in variable.table_data.items():
            self.output_structure[col] = {}
            if isinstance(row_val, dict):

                # iterate over subdict
                for row, val in row_val.items():
                    if isinstance(val, ScalarVariable):
                        self._composing_variables.append(val.name)
                        self.data[val.name] = {"row": row, "col": col, "value": None}

                    elif isinstance(val, float):
                        {"row": row, "col": col, "value": val}

            elif isinstance(row_val, ArrayVariable):
                self._composing_variables.append(row_val.name)
                self.data[val.name] = {"row": None, "col": col, "value": None}

        self.controller = controller

    def poll(self) -> Tuple[np.ndarray]:
        """
        Poll variable for value, arrange into tabular representation

        """

        output = copy.deepcopy(self.output_structure)

        vals = self.controller.get_many(self._composing_variables)

        for pvname, val in vals.items():
            self.data[pvname]["value"] = val
            output[self.data[pvname]["col"]].update({self.data[pvname]["row"]: val})

        return output
