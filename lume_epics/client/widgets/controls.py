"""
The controls module contains tools for constructing bokeh control widgets. 
Controls may be built for lume-model ScalarInputVariables.

"""

from functools import partial
from typing import Union, List
import logging

from bokeh.models import Slider, ColumnDataSource, DataTable, TableColumn, StringFormatter, StringEditor, Button
from bokeh.events import Tap

from lume_model.variables import ScalarInputVariable
from lume_epics.client.controller import Controller

logger = logging.getLogger(__name__)

class EpicsSlider:
    """EPICS based Slider used for building bokeh sliders and synchronizing process variable values.

    """

    def __init__(self, prefix: str, variable: ScalarInputVariable, controller: Controller):
        self.prefix = prefix
        self.controller = controller
        self.variable = variable
        self.build_slider()

    def build_slider(self):
        """
        Utility function for building a slider.

        Args:
            prefix (str): Prefix used for serving process variables.

            variable (ScalarInputVariable): Variable associated with the slider.

            controller (Controller): Controller object for getting process variable values.

        """
        title = self.variable.name
        if "units" in self.variable.__fields_set__:
            title += " (" + self.variable.units + ")"

        self.pvname = self.prefix + ":" + self.variable.name
        step = (self.variable.value_range[1] - self.variable.value_range[0]) / 100.0

        # construct slider
        self.bokeh_slider = Slider(
            title=title,
            value= self.variable.value_range[0],
            start=self.variable.value_range[0],
            end=self.variable.value_range[1],
            step=step,
            format = "0[.]0000"
        )

        # set up callback
        self.bokeh_slider.on_change(
            "value",
            partial(set_pv_from_slider, pvname=self.pvname, controller=self.controller),
        )

    def update(self):
        """
        Updates bokeh slider with the process variable value.

        """
        self.bokeh_slider.value = self.controller.get_value(self.pvname)


def build_sliders(
    variables: List[ScalarInputVariable], controller: Controller, prefix: str,
) -> List[Slider]:
    """
    Build sliders for a list of variables.

    Args: 
        prefix (str): Prefix used to serve process variables.

        variables (List[ScalarInputVariable]): List of variables for which to build sliders.

        controller (Controller): Controller object for getting process variable values.

    """
    sliders = []

    for variable in variables:
        slider = EpicsSlider(prefix, variable, controller,)
        sliders.append(slider)

    return sliders

def set_pv_from_slider(
    attr: str,
    old: float,
    new: float,
    pvname: str,
    controller: Controller,) -> None:
    """
    Callback function for updating process variables on slider change.

    Args:
        attr (str): Attribute to update.

        old (float): Prior slider value.

        new (float): New value assigned by slider.

        pvname (str): Name of the process variable.

        controller (Controller): Controller object for interacting with process 
            variable values.

    """
    controller.put(pvname, new)


class EntryTable:
    """
    Table of process variable names and values.

    Attriibutes:
        pv_monitors (Dict[str, PVScalar]): Monitors associated with process variables.

        output_values (dict): Dict mapping process variable name to current value.

        labels (dict): Dict mapping process variable name to labels.

        source (ColumnDataSource): Data source for populating bokeh table.



    """
    def __init__(
        self, variables: List[ScalarInputVariable], controller: Controller, prefix: str,
    ) -> None:
        """
        Initialize table.

        Args:
            variables (List[ScalarVariable]): List of variables to display.

            controller (Controller): Controller object for accessing process variables.

            prefix (str): Prefix used in setting up the server.

        """
        self.output_values = {}
        self.labels = {}
        self.prefix = prefix
        self.controller = controller

        # be sure to surface units in the table
        self.unit_map = {}

        for variable in variables:
            self.output_values[variable.name] = ""

            # check if units assigned
            if "units" in variable.__fields_set__ and variable.units:
                self.labels[variable.name] = variable.name + f" ({variable.units})"

            else:
                self.labels[variable.name] = variable.name


        self.clear_button = Button(label="Clear")
        self.clear_button.on_click(self.clear)
        self.submit_button = Button(label="Submit")
        self.submit_button.on_click(self.submit)
        self.create_table()

    def create_table(self) -> None:
        """
        Creates the bokeh table and populates variable data.
        """
        x_vals = [self.labels[var] for var in self.output_values.keys()]
        y_vals = list(self.output_values.values())
        table_data = dict(x=x_vals, values =y_vals)

        columns = [
            TableColumn(
                field="x", title="Outputs", formatter=StringFormatter(font_style="bold")
            ),
            TableColumn(field = "values", title = "Value", editor = StringEditor())
        ]

        self.source = ColumnDataSource(table_data)
        self.source.on_change('data', self.update_values)

        self.table = DataTable(
            source=self.source, columns=columns, editable=True, selectable=True, sortable=False, index_position=None, auto_edit=True
        )

    def submit(self) -> None:
        """
        Function to submit values entered into table
        """
        print("putting...")

        for variable in self.output_values:
            if self.output_values[variable] != "":
                pvname = f"{self.prefix}:{variable}"
                self.controller.put(pvname, self.output_values[variable])

    def clear(self) -> None:
        """
        Function to clear all entered values
        """
        for variable in self.output_values:
            self.output_values[variable] = ""

        x_vals = [self.labels[var] for var in self.output_values.keys()]
        y_vals = list(self.output_values.values())

        self.source.data = dict(x=x_vals, values=y_vals)


    def update_values(self, attr, new, old):

        for i, label in enumerate(new["x"]):
            self.output_values[label] = new["values"][i]