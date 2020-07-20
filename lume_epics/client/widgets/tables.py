from typing import List
import logging

from bokeh.models import ColumnDataSource, DataTable, TableColumn, StringFormatter

from lume_model.variables import ScalarVariable
from lume_epics.client.controller import Controller
from lume_epics.client.monitors import PVScalar


class ValueTable:
    """
    Table of process variable names and values.

    Attriibutes:
        pv_monitors (Dict[str, PVScalar]): Monitors associated with process variables.

        output_values (dict): Dict mapping process variable name to current value.

        unit_map (dict): Dict mapping process variable name to units.

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

            prefix (str): Prifix used in setting up the server.

        """
        # only creating pvs for non-image pvs
        self.pv_monitors = {}
        self.output_values = {}

        # be sure to surface units in the table
        self.unit_map = {}

        for variable in variables:
            self.pv_monitors[variable.name] = PVScalar(prefix, variable, controller)
            v = self.pv_monitors[variable.name].poll()

            self.output_values[variable.name] = v

            # check if units assigned
            if "units" in variable.__fields_set__:
                self.unit_map[variable.name] = variable.units

            else:
                self.unit_map[variable.name] = ""

        self.create_table()

    def create_table(self) -> None:
        """
        Creates the bokeh table and populate data.
        """
        table_data = dict(x=list(self.output_values.keys()), y=list(self.output_values.values()))
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
        Update data source to reflect updated values.
        """
        for variable in self.pv_monitors:
            v = self.pv_monitors[variable].poll()
            self.output_values[variable] = v

        self.source.data = dict(x=list(self.output_values.keys()), y=list(self.output_values.values()))
