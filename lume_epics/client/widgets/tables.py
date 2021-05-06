"""
This module contains table widgets for displaying the values of lume-model scalar
variables.

"""

from typing import List, Dict
import logging

from bokeh.models import ColumnDataSource, DataTable, TableColumn, StringFormatter

from lume_model.variables import ScalarVariable
from lume_epics.client.controller import Controller, DEFAULT_SCALAR_VALUE
from lume_epics.client.monitors import PVScalar


class ValueTable:
    """
    Table of process variable names and values.

    Attriibutes:
        _pv_monitors (Dict[str, PVScalar]): Monitors associated with process variables.

        _output_values (dict): Dict mapping process variable name to current value.

        _source (ColumnDataSource): Data source for populating bokeh table.

        _labels (Dict[str, str]): Dictionary mapping pvname to label

        _unit_map (Dict[str, str]): Dictionary mapping pvname to units

        table (DataTable): Bokeh data table

    """

    def __init__(
        self,
        variables: List[ScalarVariable],
        controller: Controller,
        labels: Dict[str, str] = {},
        sig_figs: int = 5,
    ) -> None:
        """
        Initialize table.

        Args:
            variables (List[ScalarVariable]): List of variables to display.

            controller (Controller): Controller object for accessing process variables.

            labels (Dict[list, list]): Dictionary mapping pvname to label

        """
        # only creating pvs for non-image pvs
        self._pv_monitors = {}
        self._output_values = {}
        self._labels = {}
        self._sig_figs = sig_figs

        # be sure to surface units in the table
        self._unit_map = {}

        for variable in variables:
            self._pv_monitors[variable.name] = PVScalar(variable, controller)
            v = DEFAULT_SCALAR_VALUE

            # format to sig figs
            v = format(float("{:.{p}g}".format(v, p=self._sig_figs)))
            self._output_values[variable.name] = v

            label_base = labels.get(variable.name, variable.name)

            # check if units assigned
            if "units" in variable.__fields_set__ and variable.units:
                self._labels[variable.name] = label_base + f" ({variable.units})"

            else:
                self._labels[variable.name] = label_base

        self.create_table()

    def create_table(self) -> None:
        """
        Creates the bokeh table and populates variable data.
        """
        x_vals = [self._labels[var] for var in self._output_values.keys()]
        y_vals = list(self._output_values.values())

        table_data = dict(x=x_vals, y=y_vals)
        self._source = ColumnDataSource(table_data)
        columns = [
            TableColumn(
                field="x",
                title="Variable",
                formatter=StringFormatter(font_style="bold"),
            ),
            TableColumn(field="y", title="Current Value"),
        ]

        self.table = DataTable(
            source=self._source,
            columns=columns,
            sizing_mode="stretch_both",
            index_position=None,
        )

    def update(self) -> None:
        """
        Callback function to update data source to reflect updated values.
        """
        for variable in self._pv_monitors:
            v = self._pv_monitors[variable].poll()

            # format to sig figs
            v = format(float("{:.{p}g}".format(v, p=self._sig_figs)))
            self._output_values[variable] = v

        x_vals = [self._labels[var] for var in self._output_values.keys()]
        y_vals = list(self._output_values.values())
        self._source.data = dict(x=x_vals, y=y_vals)
