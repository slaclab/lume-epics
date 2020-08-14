"""
This module contains table widgets for displaying the values of lume-model scalar 
variables.

"""

from typing import List
import logging

from bokeh.models import ColumnDataSource, DataTable, TableColumn, StringFormatter

from lume_model.variables import ScalarVariable
from lume_epics.client.controller import Controller, DEFAULT_SCALAR_VALUE
from lume_epics.client.monitors import PVScalar


class ValueTable:
    """
    Table of process variable names and values.

    Attriibutes:
        pv_monitors (Dict[str, PVScalar]): Monitors associated with process variables.

        output_values (dict): Dict mapping process variable name to current value.

        labels (dict): Dict mapping process variable name to labels.

        source (ColumnDataSource): Data source for populating bokeh table.



    """
    def __init__(
        self, variables: List[ScalarVariable], controller: Controller, prefix: str,
    ) -> None:
        """
        Initialize table.

        Args:
            variables (List[ScalarVariable]): List of variables to display.

            controller (Controller): Controller object for accessing process variables.

            prefix (str): Prefix used in setting up the server.

        """
        # only creating pvs for non-image pvs
        self.pv_monitors = {}
        self.output_values = {}
        self.labels = {}

        # be sure to surface units in the table
        self.unit_map = {}

        for variable in variables:
            self.pv_monitors[variable.name] = PVScalar(prefix, variable, controller)
        #    v = self.pv_monitors[variable.name].poll()
            v = DEFAULT_SCALAR_VALUE

            self.output_values[variable.name] = v

            # check if units assigned
            if "units" in variable.__fields_set__ and variable.units:
                self.labels[variable.name] = variable.name + f" ({variable.units})"

            else:
                self.labels[variable.name] = variable.name

        self.create_table()

    def create_table(self) -> None:
        """
        Creates the bokeh table and populates variable data.
        """
        x_vals = [self.labels[var] for var in self.output_values.keys()]
        y_vals = list(self.output_values.values())
        
        table_data = dict(x=x_vals, y=y_vals)
        self.source = ColumnDataSource(table_data)
        columns = [
            TableColumn(
                field="x", title="Outputs", formatter=StringFormatter(font_style="bold")
            ),
            TableColumn(field="y", title="Current Value"),
        ]

        self.table = DataTable(
            source=self.source, columns=columns, width=400, height=280
        )

    def update(self) -> None:
        """
        Callback function to update data source to reflect updated values.
        """
        for variable in self.pv_monitors:
            v = self.pv_monitors[variable].poll()
            self.output_values[variable] = v

        x_vals = [self.labels[var] for var in self.output_values.keys()]
        y_vals = list(self.output_values.values())
        self.source.data = dict(x=x_vals, y=y_vals)
