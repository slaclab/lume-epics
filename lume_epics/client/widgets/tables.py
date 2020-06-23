from typing import List

from bokeh.models import ColumnDataSource, DataTable, TableColumn, StringFormatter

import lume_model.variables import ScalarVariable
from lume_epics.client.controller import Controller
from lume_epics.client.monitors import PVScalar


class ValueTable:
    def __init__(
        self,
        variables: List[ScalarVariable],
        controller: Controller,
        prefix: str,
    ) -> None:
        """
        View for value table mapping variable name to value.

        Parameters
        ----------
        variables: list
            List of variables to display in table

        controller: Controller
            Controller object for getting pv values

        prefix: str
            Prefix used for the server

        """
        # only creating pvs for non-image pvs
        self.pv_monitors = {}
        self.output_values = []
        self.names = []

        # be sure to surface units in the table
        self.unit_map = {}

        for variable in variables:
            self.pv_monitors[variable.name] = PVScalar(prefix, variable, controller)
            v = self.pv_monitors[variable.name].poll()

            self.output_values.append(v)
            self.names.append(variable.name)

            # check if units assigned
            if "units" in variable.__fields_set__:
                self.unit_map[variable.name] = variable.units

            else:
                self.unit_map[variable.name] = ""

        self.create_table()

    def create_table(self) -> None:
        """
        Create the table and populate prelim data.
        """
        self.table_data = dict(x=self.names, y=self.output_values)
        self.source = ColumnDataSource(self.table_data)
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
        Update data source.
        """
        output_values = []
        for variable in self.pv_monitors:
            v = self.pv_monitors[variable].poll()
            output_values.append(v)

        self.source.data = dict(x=self.names, y=output_values)
